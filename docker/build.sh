#!/bin/bash
VERSION=${VERSION:-"latest"}
NAMESPACE=${NAMESPACE:-"agentcore/claude-code"}

# Get the ACCOUNT and REGION defined in the current configuration (default to us-west-2 if none defined)

ACCOUNT=${ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}
REGION=${REGION:-$(aws configure get region)}

# If the repository doesn't exist in ECR, create it.
aws ecr describe-repositories --region ${REGION} --repository-names "${NAMESPACE}" > /dev/null 2>&1
if [ $? -ne 0 ]
then
echo "create repository:" "${NAMESPACE}"
aws ecr create-repository --region ${REGION} --repository-name "${NAMESPACE}" > /dev/null
fi

# Log into Docker
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com
NAME="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${NAMESPACE}:${VERSION}"

echo ${NAME}

# Build docker
docker build -t ${NAME} -f Dockerfile ..

# Push it
docker push ${NAME}

