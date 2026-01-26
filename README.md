"# gemini-file-storage" 


echo "# gemini-file-storage" >> README.md
git init
git add .
git config --global user.name "clinno0617"
git config --global user.email clinno0617@gmail.com

git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/clinno0617-design/gemini-file-storage.git
git push -u origin main


# 1. 查看修改了哪些檔案(可選)
git status

# 2. 將修改的檔案加入暫存區
git add .

# 3. 提交變更
git commit -m "你的更新說明"

# 4. 推送到 GitHub
git push