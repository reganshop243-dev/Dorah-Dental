import os
import re
import sys
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime

# Run from the Django project root.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dental_clinic.settings")

import django
django.setup()

from django.apps import apps
from django.db import transaction
from django.db.models import ForeignKey, OneToOneField
from django.core.management.base import CommandError
from patients.models import Patient


# ============================================================
# DUPLICATE PATIENT MERGER
#
# RULE:
#   A patient can be considered a duplicate ONLY when:
#     1) phone numbers normalize to the same number, AND
#     2) names are the same or clearly similar.
#
# DRY RUN is the default.
#
# ACTUAL DATABASE CHANGES require:
#     python merge_duplicate_patients.py --apply
#
# ============================================================


def normalize_phone(value):
    """Normalize Ugandan/international phone formats."""
    if not value:
        return ""

    digits = re.sub(r"\D", "", str(value))

    # Uganda:
    # 0701642742 -> 256701642742
    # 701642742  -> 256701642742
    # +256701642742 -> 256701642742
    if digits.startswith("00256"):
        digits = digits[2:]

    if digits.startswith("256") and len(digits) >= 12:
        return digits

    if len(digits) == 10 and digits.startswith("0"):
        return "256" + digits[1:]

    if len(digits) == 9 and digits.startswith(("7", "3", "2")):
        return "256" + digits

    return digits


def normalize_name(value):
    if not value:
        return ""

    value = str(value).upper()
    value = re.sub(r"[^A-Z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def name_similarity(a, b):
    """Return a score from 0 to 1, handling word-order changes."""
    a = normalize_name(a)
    b = normalize_name(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    # Same words in different order.
    a_sorted = " ".join(sorted(a.split()))
    b_sorted = " ".join(sorted(b.split()))

    direct = SequenceMatcher(None, a, b).ratio()
    sorted_ratio = SequenceMatcher(None, a_sorted, b_sorted).ratio()

    a_tokens = set(a.split())
    b_tokens = set(b.split())

    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    token_jaccard = len(intersection) / len(union) if union else 0.0

    # Strong support when the shorter name's words are contained in the longer.
    subset_ratio = (
        len(a_tokens & b_tokens) / min(len(a_tokens), len(b_tokens))
        if min(len(a_tokens), len(b_tokens))
        else 0.0
    )

    return max(direct, sorted_ratio, token_jaccard, subset_ratio * 0.92)


def display_name(patient):
    return f"{patient.first_name} {patient.last_name}".strip()


def patient_phones(patient):
    """
    Return all normalized phone representations we can safely compare.
    Patient currently has one phone field, but this also tolerates
    comma/semicolon/slash-separated values.
    """
    raw = str(patient.phone or "")
    parts = re.split(r"[,;/|]+", raw)

    phones = set()
    for part in parts:
        p = normalize_phone(part)
        if p:
            phones.add(p)

    return phones


def collect_patient_relations():
    """
    Discover every model field that points to Patient.

    This is safer than hard-coding only Appointment and Invoice:
    treatments, dental charts, images, portal records, etc. are
    also preserved when they have a Patient FK.
    """
    relations = []

    for model in apps.get_models():
        for field in model._meta.get_fields():
            if not getattr(field, "is_relation", False):
                continue

            if not isinstance(field, (ForeignKey, OneToOneField)):
                continue

            if field.remote_field.model is not Patient:
                continue

            relations.append((model, field))

    return relations


def choose_survivor(a, b):
    """
    Keep the older patient record by ID as the stable/original record.
    This avoids arbitrarily replacing the existing patient.
    """
    return (a, b) if a.pk < b.pk else (b, a)


def find_duplicate_groups():
    patients = list(
        Patient.objects.all().order_by("id")
    )

    # phone -> patients
    by_phone = defaultdict(list)

    for patient in patients:
        for phone in patient_phones(patient):
            by_phone[phone].append(patient)

    pairs = []
    seen_pairs = set()

    for phone, group in by_phone.items():
        if len(group) < 2:
            continue

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a = group[i]
                b = group[j]

                pair_key = tuple(sorted((a.pk, b.pk)))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                score = name_similarity(
                    display_name(a),
                    display_name(b),
                )

                # Same phone + clearly similar name.
                # 0.82 catches normal spelling mistakes while avoiding
                # loose name-only matching.
                if score >= 0.82:
                    pairs.append({
                        "a": a,
                        "b": b,
                        "phone": phone,
                        "score": score,
                    })

    # Convert pair matches into connected groups.
    # If A matches B and B matches C, they are reviewed as one group.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for item in pairs:
        union(item["a"].pk, item["b"].pk)

    grouped = defaultdict(list)

    patient_by_id = {p.pk: p for p in patients}

    for item in pairs:
        grouped[find(item["a"].pk)].append(item["a"].pk)
        grouped[find(item["b"].pk)].append(item["b"].pk)

    groups = []
    for ids in grouped.values():
        unique_ids = sorted(set(ids))
        if len(unique_ids) > 1:
            groups.append([patient_by_id[x] for x in unique_ids])

    return groups, pairs


def print_report(groups, pairs, relations):
    print("=" * 90)
    print("DUPLICATE PATIENT AUDIT — DRY RUN")
    print("=" * 90)
    print("Database changes: NONE")
    print("Rule: SAME NORMALIZED PHONE + SIMILAR NAME")
    print()

    if not groups:
        print("No duplicate patient groups found.")
        return

    pair_scores = {}
    for item in pairs:
        key = tuple(sorted((item["a"].pk, item["b"].pk)))
        pair_scores[key] = item

    print(f"Potential duplicate groups: {len(groups)}")
    print()

    for number, group in enumerate(groups, 1):
        survivor, _ = choose_survivor(group[0], group[1])

        print("-" * 90)
        print(f"GROUP {number}")
        print("-" * 90)

        for patient in group:
            phones = ", ".join(sorted(patient_phones(patient))) or "(NO PHONE)"

            appointment_count = 0
            invoice_count = 0

            for model, field in relations:
                if model.__name__ == "Appointment":
                    appointment_count += model.objects.filter(
                        **{field.name: patient}
                    ).count()
                elif model.__name__ == "Invoice":
                    invoice_count += model.objects.filter(
                        **{field.name: patient}
                    ).count()

            marker = "KEEP" if patient.pk == survivor.pk else "MERGE"

            print(
                f"[{marker}] Patient ID={patient.pk} | "
                f"{display_name(patient)} | "
                f"Phone={phones} | "
                f"Appointments={appointment_count} | "
                f"Invoices={invoice_count}"
            )

        print()

    print("=" * 90)
    print("IMPORTANT")
    print("=" * 90)
    print("Nothing has been changed.")
    print()
    print("When this report is confirmed, run:")
    print("python merge_duplicate_patients.py --apply")
    print()


def backup_summary(groups, relations):
    """
    Produce a text summary immediately before apply.
    The database operation itself is wrapped in transaction.atomic().
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"duplicate_merge_backup_{stamp}.txt",
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write("DUPLICATE PATIENT MERGE BACKUP SUMMARY\n")
        f.write(f"Created: {datetime.now().isoformat()}\n\n")

        for group_no, group in enumerate(groups, 1):
            f.write(f"GROUP {group_no}\n")
            for patient in group:
                f.write(
                    f"Patient ID={patient.pk} | "
                    f"{display_name(patient)} | "
                    f"Phone={patient.phone or ''}\n"
                )

                for model, field in relations:
                    qs = model.objects.filter(**{field.name: patient})

                    count = qs.count()
                    if count:
                        f.write(
                            f"  {model._meta.label}.{field.name}: {count} records\n"
                        )

            f.write("\n")

    return path


def merge_group(group, relations):
    survivor = min(group, key=lambda p: p.pk)
    duplicates = [p for p in group if p.pk != survivor.pk]

    moved = defaultdict(int)
    deleted_related = defaultdict(int)

    for duplicate in duplicates:
        for model, field in relations:
            qs = model.objects.filter(**{field.name: duplicate})

            if isinstance(field, OneToOneField):
                # If the survivor already has this one-to-one record,
                # preserve the survivor's record and remove the duplicate's
                # conflicting one-to-one record.
                existing = model.objects.filter(
                    **{field.name: survivor}
                ).first()

                if existing:
                    count = qs.count()
                    if count:
                        qs.delete()
                        deleted_related[model._meta.label] += count
                    continue

            count = qs.update(**{field.name: survivor.pk})
            moved[model._meta.label] += count

        # Delete ONLY the duplicate patient after all linked records
        # have been reassigned.
        duplicate.delete()

    return survivor, duplicates, moved, deleted_related


def main():
    apply = "--apply" in sys.argv

    groups, pairs = find_duplicate_groups()
    relations = collect_patient_relations()

    if not apply:
        print_report(groups, pairs, relations)
        return

    if not groups:
        print("No duplicate patient groups found. Nothing to change.")
        return

    print("=" * 90)
    print("DUPLICATE PATIENT MERGE — APPLY MODE")
    print("=" * 90)
    print(f"Groups to merge: {len(groups)}")
    print()

    backup = backup_summary(groups, relations)
    print(f"Pre-merge summary saved to: {backup}")
    print()

    total_patients_deleted = 0
    total_records_moved = defaultdict(int)
    total_related_deleted = defaultdict(int)

    try:
        with transaction.atomic():
            for group in groups:
                survivor, duplicates, moved, deleted_related = merge_group(
                    group,
                    relations,
                )

                print(
                    f"MERGED: {', '.join(display_name(p) for p in duplicates)} "
                    f"-> KEEP ID {survivor.pk} ({display_name(survivor)})"
                )

                total_patients_deleted += len(duplicates)

                for model_name, count in moved.items():
                    total_records_moved[model_name] += count

                for model_name, count in deleted_related.items():
                    total_related_deleted[model_name] += count

    except Exception:
        print()
        print("ERROR: transaction rolled back.")
        raise

    print()
    print("=" * 90)
    print("MERGE COMPLETE")
    print("=" * 90)
    print(f"Duplicate patient records deleted: {total_patients_deleted}")

    print("\nRecords reassigned:")
    for model_name, count in sorted(total_records_moved.items()):
        print(f"  {model_name}: {count}")

    if total_related_deleted:
        print("\nConflicting one-to-one records removed:")
        for model_name, count in sorted(total_related_deleted.items()):
            print(f"  {model_name}: {count}")

    print()
    print("Appointments and invoices were reassigned, not deleted.")
    print(f"Backup summary: {backup}")


if __name__ == "__main__":
    main()
