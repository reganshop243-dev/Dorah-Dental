"""
Download all static files for offline use
"""
import os
import requests
from pathlib import Path
import time

def download_file(url, dest_path, retries=3):
    """Download a file with retry and progress"""
    for attempt in range(retries):
        try:
            print(f"  Attempt {attempt + 1}: {os.path.basename(dest_path)}")
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r    Progress: {percent:.1f}%", end='')
                print(f"\r  ✅ Downloaded: {os.path.basename(dest_path)}")
                return True
            else:
                print(f"  ❌ Failed: {url} (Status: {response.status_code})")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            time.sleep(1)
    return False

def main():
    """Download all static files"""
    static_dir = Path('static')
    
    # Create directories
    (static_dir / 'css').mkdir(parents=True, exist_ok=True)
    (static_dir / 'js').mkdir(parents=True, exist_ok=True)
    (static_dir / 'webfonts').mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("  📥 DOWNLOADING STATIC FILES FOR OFFLINE USE")
    print("=" * 60)
    
    files_to_download = [
        # Bootstrap 5.3.0
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
            'dest': static_dir / 'css/bootstrap.min.css'
        },
        {
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
            'dest': static_dir / 'js/bootstrap.bundle.min.js'
        },
        # Font Awesome 6.4.0
        {
            'url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
            'dest': static_dir / 'css/font-awesome.min.css'
        },
        {
            'url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2',
            'dest': static_dir / 'webfonts/fa-solid-900.woff2'
        },
        {
            'url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2',
            'dest': static_dir / 'webfonts/fa-regular-400.woff2'
        },
        {
            'url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2',
            'dest': static_dir / 'webfonts/fa-brands-400.woff2'
        },
        {
            'url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-v4compatibility.woff2',
            'dest': static_dir / 'webfonts/fa-v4compatibility.woff2'
        },
        # jQuery 3.6.0
        {
            'url': 'https://code.jquery.com/jquery-3.6.0.min.js',
            'dest': static_dir / 'js/jquery.min.js'
        },
    ]
    
    success_count = 0
    for item in files_to_download:
        print(f"\n📥 Downloading: {os.path.basename(item['dest'])}")
        if download_file(item['url'], item['dest']):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"  📦 Download complete! {success_count}/{len(files_to_download)} files downloaded")
    print(f"  📁 Files saved to: {static_dir.absolute()}")
    print("=" * 60)
    
    if success_count < len(files_to_download):
        print("\n⚠️ Some files failed to download. Please check your internet connection.")
        print("   You can try running the script again.")
    else:
        print("\n✅ All static files downloaded successfully!")
        print("   The application will now work offline.")

if __name__ == '__main__':
    # Check if requests is installed
    try:
        import requests
    except ImportError:
        print("Installing requests...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
        import requests
    
    main()