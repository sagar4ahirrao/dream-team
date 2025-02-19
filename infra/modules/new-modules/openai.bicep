param location string = resourceGroup().location
param azureOpenaiResourceName string
param azureOpenaiDeploymentName string
param azureOpenaiDeploymentNameMini string
param customSubDomainName string
param dailyRateLimit int

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: azureOpenaiResourceName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: customSubDomainName
    dailyRateLimit: dailyRateLimit   
  }
}

// Define the OpenAI deployment
resource openaideployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: azureOpenaiDeploymentName
  parent: openai
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      name: 'gpt-4o'
      format: 'OpenAI'
      version: '2024-11-20'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

resource openaideploymentminiNew 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: azureOpenaiDeploymentNameMini
  parent: openai
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      name: 'gpt-4o-mini'
      format: 'OpenAI'
      version: '2024-07-18'
      
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
  dependsOn: [openaideployment]
}

output openaiId string = openai.id
output openaiEndpoint string = openai.properties.endpoint

