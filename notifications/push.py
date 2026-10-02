import os,json,base64

def send_patient_push(patient,title,body,data=None):
    tokens=list(patient.mobile_device_tokens.filter(is_active=True).values_list('token',flat=True))
    if not tokens:return {'sent':0,'reason':'no_device_tokens'}
    try:
        import firebase_admin
        from firebase_admin import credentials,messaging
    except ImportError:return {'sent':0,'reason':'firebase_admin_not_installed'}
    try:
        if not firebase_admin._apps:
            raw=os.environ.get('FIREBASE_CREDENTIALS_JSON')
            if os.environ.get('FIREBASE_CREDENTIALS_JSON_BASE64'):raw=base64.b64decode(os.environ['FIREBASE_CREDENTIALS_JSON_BASE64']).decode()
            if not raw:return {'sent':0,'reason':'firebase_credentials_missing'}
            cred=credentials.Certificate(raw if os.path.exists(raw) else json.loads(raw));firebase_admin.initialize_app(cred)
        sent=0;failed=[]
        for t in tokens:
            try:
                messaging.send(messaging.Message(notification=messaging.Notification(title=title,body=body),data={str(k):str(v) for k,v in (data or {}).items()},token=t));sent+=1
            except Exception:failed.append(t)
        if failed:patient.mobile_device_tokens.filter(token__in=failed).update(is_active=False)
        return {'sent':sent,'failed':len(failed)}
    except Exception as exc:return {'sent':0,'reason':str(exc)}
