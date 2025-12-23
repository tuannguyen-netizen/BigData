# Quick Commands - Upload to GitHub

## Bước 1: Stage tất cả thay đổi

```bash
cd /home/tuan_nguyen/Tuan/Project/BigData/BigData/final_project

# Add tất cả files mới và thay đổi
git add .
```

## Bước 2: Commit với message

```bash
git commit -m "refactor: reorganize project structure for better maintainability

Major Changes:
- Moved 13 documentation files to docs/archived/
- Created consolidated ARCHITECTURE.md
- Reorganized 19 scripts into 5 categorized subdirectories
- Added .gitignore and .env.example
- Deleted redundant backup files and logs
- Moved predict_service.py to web/ directory
- Updated README with new structure

Benefits:
- 88% reduction in root-level markdown files (17 → 2)
- Clear separation of concerns
- Professional project structure"
```

## Bước 3: Kiểm tra remote (nếu đã có)

```bash
git remote -v
```

**Nếu chưa có remote**, thêm remote:

```bash
# Thay YOUR_USERNAME và YOUR_REPO_NAME
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

## Bước 4: Push lên GitHub

```bash
# Nếu lần đầu push
git push -u origin main

# Hoặc nếu branch là master
git push -u origin master

# Hoặc push branch hiện tại
git push -u origin HEAD
```

**Nếu gặp lỗi authentication**, dùng Personal Access Token:

```bash
# Tạo token tại: https://github.com/settings/tokens
# Sau đó:
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## Xong! ✅

Kiểm tra trên GitHub để xác nhận.
