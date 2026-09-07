# Deliberately minimal and separate from backend/Dockerfile: this image
# only ever needs to parse HCL and run Checkov against an uploaded .tf
# file. It never installs FastAPI, SQLAlchemy, or the OpenAI SDK, and is
# never given OPENAI_API_KEY, DATABASE_URL, or any other app secret --
# sandbox_runner.py (in the backend) launches it with an explicitly empty
# environment and no network access. Keeping this image's dependency list
# short keeps its attack surface short too.
FROM python:3.11-slim

RUN pip install --no-cache-dir python-hcl2 checkov

# Runs as a non-root user -- if anything inside an uploaded .tf file (or a
# Checkov check it triggers) tried to escalate, it starts from an account
# with no special privileges on this filesystem.
RUN useradd --create-home --uid 1000 sandboxuser

COPY sandbox_runtime.py /app/sandbox_runtime.py
WORKDIR /app
USER sandboxuser

ENTRYPOINT ["python", "sandbox_runtime.py"]
