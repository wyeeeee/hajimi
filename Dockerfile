FROM python:3.11-slim

WORKDIR /app

# 设置pip使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 首先只复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 然后复制应用代码
COPY . .

# 确保data目录存在
RUN mkdir -p /app/data && chmod 777 /app/data

# 确保templates目录有正确权限
RUN chmod -R 755 /app/app/templates

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
