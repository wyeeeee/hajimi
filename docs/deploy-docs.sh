#!/bin/bash

# Hajimi 文档部署脚本
# 用于将文档推送到 doc 分支并触发自动部署

echo "🚀 开始部署 Hajimi 文档..."

# 检查是否有未提交的更改
if [[ -n $(git status --porcelain) ]]; then
    echo "⚠️  检测到未提交的更改，请先提交所有更改"
    git status
    exit 1
fi

# 获取当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 当前分支: $CURRENT_BRANCH"

# 检查是否已经在 doc 分支
if [ "$CURRENT_BRANCH" = "doc" ]; then
    echo "✅ 已在 doc 分支，直接推送..."
    git push origin doc
else
    echo "🔄 切换到 doc 分支..."
    
    # 检查 doc 分支是否存在
    if git show-ref --verify --quiet refs/heads/doc; then
        echo "📂 doc 分支已存在，切换到该分支"
        git checkout doc
        
        # 合并当前分支的更改
        echo "🔄 合并 $CURRENT_BRANCH 分支的更改..."
        git merge $CURRENT_BRANCH --no-edit
    else
        echo "📂 创建新的 doc 分支"
        git checkout -b doc
    fi
    
    # 推送到远程
    echo "📤 推送到远程 doc 分支..."
    git push origin doc
    
    # 切换回原分支
    echo "🔄 切换回 $CURRENT_BRANCH 分支..."
    git checkout $CURRENT_BRANCH
fi

echo "✅ 文档部署完成！"
echo "🌐 GitHub Actions 将自动构建并部署到 GitHub Pages"
echo "📖 访问地址: https://wyeeeee.github.io/hajimi/"
echo ""
echo "💡 提示: 可以在 GitHub 仓库的 Actions 标签页查看构建状态"