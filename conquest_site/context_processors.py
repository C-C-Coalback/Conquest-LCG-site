import os
from pathlib import Path

def version_info(request):
    """Provide version information to templates."""
    version = None
    base_dir = Path(__file__).resolve().parent.parent
    
    # Try to read git commit hash from .git/HEAD
    try:
        git_head = base_dir / '.git' / 'HEAD'
        if git_head.exists():
            head_content = git_head.read_text().strip()
            # If HEAD points to a ref, follow it
            if head_content.startswith('ref:'):
                ref_path = head_content.split(' ', 1)[1].strip()
                ref_file = base_dir / '.git' / ref_path
                if ref_file.exists():
                    commit_hash = ref_file.read_text().strip()[:7]
                    version = f"git commit:{commit_hash}"
            else:
                # Detached HEAD - direct hash
                version = f"git commit:{head_content[:7]}"
    except (OSError, IOError):
        pass
    
    # If no git info, check for VERSION file
    if not version:
        version_file = base_dir / 'VERSION'
        if version_file.exists():
            version = version_file.read_text().strip()
    
    # Fallback
    if not version:
        version = "unknown"
    
    return {'site_version': version}
