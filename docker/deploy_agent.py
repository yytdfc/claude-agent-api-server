import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

response = client.create_agent_runtime(
    agentRuntimeName='claude_code_2',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': '236995464743.dkr.ecr.us-west-2.amazonaws.com/agentcore/claude-code:latest'
        }
    },
    networkConfiguration={"networkMode": "PUBLIC"},
    authorizerConfiguration={
        'customJWTAuthorizer': {
            'discoveryUrl': 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_Sw8yyFfBT/.well-known/openid-configuration',
            'allowedClients': [
                '2d2cqqjvpf1ecqjg6gh1u6fivl',
            ]
        }
    },
    # roleArn='arn:aws:iam::236995464743:role/AgentRuntimeRole'
    roleArn='arn:aws:iam::236995464743:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2-fdd34a21fd',
    requestHeaderConfiguration={
        "requestHeaderAllowlist": ["Authorization"],
    },
)

print(f"Agent Runtime created successfully!")
print(f"Agent Runtime ARN: {response['agentRuntimeArn']}")
print(f"Status: {response['status']}")

