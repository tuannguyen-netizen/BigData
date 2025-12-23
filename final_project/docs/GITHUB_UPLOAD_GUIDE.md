# Hướng Dẫn Cập Nhật Lên GitHub

## Bước 1: Kiểm Tra Git Repository

Kiểm tra xem dự án đã có git repository chưa:

```bash
cd /home/tuan_nguyen/Tuan/Project/BigData/BigData/final_project
git status
```

**Nếu chưa có git repository**, khởi tạo:

```bash
git init
```

## Bước 2: Kiểm Tra Files Sẽ Commit

Xem các files đã thay đổi:

```bash
git status
```

Xem chi tiết thay đổi:

```bash
git diff
```

## Bước 3: Stage Tất Cả Files

Add tất cả files mới và đã thay đổi:

```bash
git add .
```

**Hoặc** add từng loại file cụ thể:

```bash
# Add documentation
git add docs/ README.md QUICK_START.md

# Add configuration files
git add .gitignore .env.example config/

# Add reorganized scripts
git add scripts/

# Add moved Python files
git add web/predict_service.py
```

## Bước 4: Commit Changes

Commit với message mô tả chi tiết:

```bash
git commit -m "refactor: reorganize project structure for better maintainability

Major Changes:
- Moved 13 documentation files to docs/archived/
- Created consolidated ARCHITECTURE.md
- Reorganized 19 scripts into 5 categorized subdirectories (setup, workers, checks, fixes, utils)
- Added .gitignore and .env.example
- Deleted 5 redundant files (backups, logs, duplicates)
- Moved predict_service.py to web/ directory
- Moved kafka_docker_compose_fixed.yml to config/
- Updated README with new structure

Benefits:
- 88% reduction in root-level markdown files (17 → 2)
- Clear separation of concerns
- Better discoverability with README files in each directory
- Professional project structure following industry best practices"
```

## Bước 5: Kết Nối Với GitHub Repository

### Nếu Chưa Có Remote Repository

**5.1. Tạo repository mới trên GitHub:**
- Vào https://github.com
- Click "New repository"
- Đặt tên repository (ví dụ: `bigdata-final-project`)
- **KHÔNG** chọn "Initialize with README" (vì đã có sẵn)
- Click "Create repository"

**5.2. Kết nối local repository với GitHub:**

```bash
# Thay YOUR_USERNAME và YOUR_REPO_NAME
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Hoặc dùng SSH (nếu đã setup SSH key)
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

**5.3. Đổi tên branch chính thành main (nếu cần):**

```bash
git branch -M main
```

### Nếu Đã Có Remote Repository

Kiểm tra remote hiện tại:

```bash
git remote -v
```

Nếu cần update URL:

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

## Bước 6: Push Lên GitHub

### Lần Đầu Push (với new repository)

```bash
git push -u origin main
```

**Nếu gặp lỗi "failed to push some refs"**, có thể cần pull trước:

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Push Thông Thường

```bash
git push
```

## Bước 7: Xác Nhận Trên GitHub

1. Truy cập repository trên GitHub
2. Kiểm tra:
   - ✅ Cấu trúc thư mục mới
   - ✅ README.md hiển thị đúng
   - ✅ `docs/` directory với documentation
   - ✅ `scripts/` với 5 subdirectories
   - ✅ `.gitignore` hoạt động (không có `__pycache__`, `*.log`)

## Bước 8: Tạo Release/Tag (Tùy Chọn)

Đánh dấu version sau khi cleanup:

```bash
# Tạo tag
git tag -a v2.0.0 -m "Version 2.0.0 - Reorganized project structure"

# Push tag lên GitHub
git push origin v2.0.0
```

Hoặc tạo Release trên GitHub UI:
- Vào tab "Releases"
- Click "Create a new release"
- Chọn tag `v2.0.0`
- Tiêu đề: "v2.0.0 - Clean Code Structure"
- Mô tả: Copy nội dung từ walkthrough.md

## Troubleshooting

### Lỗi: Authentication Failed

**Giải pháp 1: Dùng Personal Access Token**

```bash
# Thay YOUR_TOKEN bằng token từ GitHub Settings > Developer settings > Personal access tokens
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

**Giải pháp 2: Dùng SSH**

```bash
# Tạo SSH key (nếu chưa có)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub

# Add vào GitHub Settings > SSH and GPG keys
# Sau đó đổi remote URL
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

### Lỗi: Large Files

Nếu có files quá lớn (>100MB):

```bash
# Thêm vào .gitignore
echo "data/*.csv" >> .gitignore
echo "models/" >> .gitignore

# Remove từ staging
git rm --cached data/*.csv
git rm --cached -r models/

# Commit lại
git add .gitignore
git commit -m "chore: ignore large data files"
```

### Lỗi: Merge Conflicts

Nếu có conflicts khi pull:

```bash
# Xem files conflict
git status

# Sửa conflicts trong files
# Sau đó:
git add .
git commit -m "fix: resolve merge conflicts"
git push
```

## Best Practices

### 1. Commit Messages

Dùng conventional commits:
- `feat:` - Tính năng mới
- `fix:` - Sửa lỗi
- `refactor:` - Refactor code
- `docs:` - Cập nhật documentation
- `chore:` - Maintenance tasks

### 2. .gitignore

Đảm bảo `.gitignore` đã được tạo và hoạt động:

```bash
# Kiểm tra files sẽ bị ignore
git status --ignored
```

### 3. Branch Strategy

Nếu làm việc nhóm:

```bash
# Tạo branch cho feature mới
git checkout -b feature/new-feature

# Sau khi hoàn thành
git checkout main
git merge feature/new-feature
git push
```

### 4. README Badges (Tùy Chọn)

Thêm badges vào README.md:

```markdown
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Spark](https://img.shields.io/badge/spark-4.0.0-orange.svg)
![Kafka](https://img.shields.io/badge/kafka-3.8.0-black.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
```

## Quick Commands Reference

```bash
# Workflow cơ bản
git status                    # Xem trạng thái
git add .                     # Stage tất cả
git commit -m "message"       # Commit
git push                      # Push lên GitHub

# Xem history
git log --oneline            # Xem commit history
git diff                     # Xem thay đổi

# Undo changes
git restore file.py          # Undo changes chưa stage
git restore --staged file.py # Unstage file
git reset --soft HEAD~1      # Undo commit cuối (giữ changes)

# Branch management
git branch                   # List branches
git checkout -b new-branch   # Tạo và switch branch
git merge branch-name        # Merge branch
```

## Kết Quả Mong Đợi

Sau khi hoàn thành, GitHub repository sẽ có:

✅ Cấu trúc thư mục rõ ràng, chuyên nghiệp  
✅ Documentation được tổ chức tốt trong `docs/`  
✅ Scripts được phân loại trong `scripts/`  
✅ `.gitignore` ngăn files không cần thiết  
✅ `.env.example` hướng dẫn configuration  
✅ README.md với project structure mới  
✅ Commit history sạch sẽ với message rõ ràng  

---

**Chúc bạn thành công! 🚀**
