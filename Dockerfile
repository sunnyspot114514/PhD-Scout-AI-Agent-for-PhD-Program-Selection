# 1. 使用官方的 Python 镜像作为基础
#    建议使用一个较新的、包含 Streamlit 和 Python 的版本
#    例如：python:3.10-slim (可以根据你的需求调整 Python 版本)
FROM python:3.10-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖文件
#    先复制 requirements.txt，这样 Docker 可以缓存这一层。
#    如果 requirements.txt 没有改变，后续构建会更快。
COPY requirements.txt ./

# 4. 安装 Python 依赖
#    使用 --no-cache-dir 避免镜像膨胀
#    使用 --default-timeout=100 增加超时时间，防止网络问题导致安装失败
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 5. 复制你的项目代码
COPY . .

# 6. 设置环境变量 (可选，但推荐)
#    HF Spaces 会自动将 Secrets 注入到环境变量中
#    例如：
# ENV TAVILY_API_KEY=$TAVILY_API_KEY
# ENV OPENAI_API_KEY=$OPENAI_API_KEY
# ENV DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
# ENV SEMANTIC_SCHOLAR_API_KEY=$SEMANTIC_SCHOLAR_API_KEY
#    注意：你的 app.py 中是从 sidebar 获取 API Key 的，所以这里不强制设置。
#          但如果 main.py 有直接从 os.environ 获取的部分，就需要这里设置。
#          根据你 app.py 的逻辑，API Key 是通过用户输入，所以这里可以不用设置。

# 7. 暴露 Streamlit 运行的端口
EXPOSE 8501

# 8. 定义容器启动时运行的命令
#    使用 streamlit run app.py --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false
#    --server.port 8501 是 Streamlit 默认的端口，HF Spaces 需要这个端口
#    --server.enableCORS false 和 --server.enableXsrfProtection false 有时在某些环境中可以避免一些奇奇怪怪的错误
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]