# 1. 查看修改了哪些檔案(可選)
git status

# 2. 將修改的檔案加入暫存區
git add .

# 3. 提交變更
git commit -m “update!"
git commit -m "update %date:~0,4%-%date:~5,2%-%date:~8,2% %time:~0,2%:%time:~3,2%:%time:~6,2%"


# 4. 推送到 GitHub
git push
