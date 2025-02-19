param azureOpenaiResourceName string
param azureOpenaiDeploymentName string
param azureOpenaiDeploymentNameMini string

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: azureOpenaiResourceName
}

// Define the OpenAI deployment
resource openaideployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' existing = {
  name: azureOpenaiDeploymentName
}

resource openaideploymentmini 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' existing = {
  name: azureOpenaiDeploymentNameMini
}

output openaiId string = openai.id
output openaiEndpoint string = openai.properties.endpoint
