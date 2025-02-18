param location string = resourceGroup().location
param azureOpenaiResourceName string
param azureOpenaiDeploymentName string
param azureOpenaiDeploymentNameMini string
param userPrincipalId string
param identityName string

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

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource userOpenaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, userPrincipalId, 'Cognitive Services OpenAI User')
  scope: openai
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
} 

resource appOpenaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, identity.id, 'Cognitive Services OpenAI User')
  scope: openai
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

output openaiId string = openai.id
output openaiEndpoint string = openai.properties.endpoint
