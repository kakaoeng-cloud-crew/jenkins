# import boto3
# import db_utils as db  # db 접근을 위한 모듈
import subprocess
import argparse
# from os import getenv
# from bson import ObjectId

parser = argparse.ArgumentParser()
parser.add_argument('--project_name', type=str, required=True)
parser.add_argument('--project_id', type=str, required=True)
args = parser.parse_args()
project_name = args.project_name
project_id = args.project_id

try:
    result = subprocess.run(
        ["sudo", "helm", "delete", project_name],
        check=True,
        text=True,
        capture_output=True
    )
    print(f"Helm chart for project '{project_name}' deleted successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    # 명령어 실행 중 에러가 발생한 경우
    print(f"Failed to delete Helm chart for project '{project_name}'.")
    print("Error:", e.stderr)
    exit(1)

try:
    result = subprocess.run(
        ["sudo", "kubectl", "delete", 'namespace', project_name],
        check=True,
        text=True,
        capture_output=True
    )
    print(f"kubernetes namespace '{project_name}' deleted successfully.")
    print("Output:", result.stdout)
except subprocess.CalledProcessError as e:
    # 명령어 실행 중 에러가 발생한 경우
    print(f"Failed to delete namespace for k8s '{project_name}'.")
    print("Error:", e.stderr)
    exit(1)
