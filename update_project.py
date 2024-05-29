import db_utils as db  # db 접근을 위한 모듈
import subprocess
import argparse
from os import getenv
from bson import ObjectId

# subprocess 모듈
def run_subprocess(command):
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command '{' '.join(command)}' failed.")
        print("Error:", e.stderr.strip())
        exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('--project_name', type=str, required=True)
parser.add_argument('--project_id', type=str, required=True)
args = parser.parse_args()
project_name = args.project_name
project_id = args.project_id

# MongoDB에서 ObjectId로 조회
try:
    project_data = collection.find_one({"_id": ObjectId(project_id)})
    if not project_data:
        print(f"No project found with id '{project_id}'.")
        exit(1)
except Exception as e:
    print(f"Error while fetching project data: {e}")
    exit(1)

values_url = project_data.get('values_url')
if not values_url:
    print("Values URL is missing in the project data.")
    exit(1)

template_file = f"/helm/{project_id}/{project_name}_template.tgz"
values_file = f"/helm/{project_id}/{project_name}_values.yaml"
# values.yaml 다운로드
print(f"Downloading Helm values file from {values_url} to {values_file}...")
run_subprocess(["sudo", "aws", "s3", "cp", values_url, values_file])
print("Helm values file downloaded successfully.")

run_subprocess(["sudo", "helm", "upgrade", project_name, template_file, "-n", project_name, "--values", values_file])
print("Helm upgrade successfully.")

# 메타 데이터 업데이트 하기
data = {
    "helm_name": "",
    "last_deployed": "",
    "namespace": "",
    "status": "",
    "revision": 0,
    "chart": "",
    "app_version": ""
}

first = run_subprocess(["sudo", "helm", "status", project_name, "-n", project_name])
for line in first.splitlines():
    if line.startswith("NAME:"):
        data["helm_name"] = line.split(":", 1)[1].strip()
    elif line.startswith("LAST DEPLOYED:"):
        data["last_deployed"] = line.split(":", 1)[1].strip()
    elif line.startswith("NAMESPACE:"):
        data["namespace"] = line.split(":", 1)[1].strip()
    elif line.startswith("STATUS:"):
        data["status"] = line.split(":", 1)[1].strip()
    elif line.startswith("REVISION:"):
        data["revision"] = int(line.split(":", 1)[1].strip())

# 첫 번째 명령어 실행
first = subprocess.Popen(
    ["sudo", "helm", "list", "-n", project_name], 
    stdout=subprocess.PIPE, 
    text=True
)

# 두 번째 명령어 실행
second = subprocess.run(
    ["gawk", 'NR==2 {print $9 " " $10}'], 
    stdin=first.stdout, 
    stdout=subprocess.PIPE, 
    text=True,
    check=True
)
first.stdout.close()
second = second.stdout.strip()
data["chart"], data["app_version"] = second.split(' ', 1)

print(data)

# 몽고 DB에 업데이트하기
try:
    result = collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"meta_data": data}}
    )
    if result.matched_count > 0:
        print(f"Project '{project_id}' updated successfully with metadata '{data}'.")
    else:
        print(f"No project found with id '{project_id}' to update.")
except Exception as e:
    print(f"Error while updating project data: {e}")
    exit(1)
