# aws ecr create-repository --repository-name claude-code-agentcore --region us-west-2
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 236995464743.dkr.ecr.us-west-2.amazonaws.com

docker build -t 236995464743.dkr.ecr.us-west-2.amazonaws.com/claude-code-agentcore:latest -f Dockerfile ..
# docker build -t 236995464743.dkr.ecr.us-west-2.amazonaws.com/claude-code-agentcore:latest .

# docker run -p 8080:8080 236995464743.dkr.ecr.us-west-2.amazonaws.com/claude-code-agentcore:latest

# docker push 236995464743.dkr.ecr.us-west-2.amazonaws.com/claude-code-agentcore:latest

# aws ecr describe-images --repository-name claude-code-agentcore --region us-west-2
