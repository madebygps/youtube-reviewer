#:sdk Aspire.AppHost.Sdk@13.0.0
#:package Aspire.Hosting.JavaScript@13.0.0
#:package Aspire.Hosting.Python@13.0.0
#:package dotenv.net@4.0.0

using dotenv.net;

var envVars = DotEnv.Read();

var builder = DistributedApplication.CreateBuilder(args);
#pragma warning disable ASPIREHOSTINGPYTHON001

envVars.TryGetValue("APPLICATIONINSIGHTS_CONNECTION_STRING", out string? appInsightsConnectionString);

var ytAgent = builder.AddPythonModule("yt-agent", "./app/", "yt_agent")
    .WithUv()
    .WithHttpEndpoint(env: "PORT")
    .WithHttpHealthCheck("/health")
    .WithEnvironment("OTEL_PYTHON_EXCLUDED_URLS", "/health")
    // OpenAI settings
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_GPT5", envVars["AZURE_OPENAI_ENDPOINT_GPT5"])
    .WithEnvironment("AZURE_OPENAI_API_KEY_GPT5", envVars["AZURE_OPENAI_API_KEY_GPT5"])
    .WithEnvironment("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5", envVars["AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"])
    .WithEnvironment("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", envVars["AZURE_OPENAI_ENDPOINT_VERSION_GPT5"])
    .WithTracing(appInsightsConnectionString)
    .WithExternalHttpEndpoints();

var app = builder.AddUvicornApp("app", "./app", "main:app")
    .WithUv()
    .WithExternalHttpEndpoints()
    .WithHttpHealthCheck("/health");

var frontend = builder.AddViteApp("frontend", "./frontend")
    .WithReference(app)
    .WaitFor(app);

app.PublishWithContainerFiles(frontend, "./static");

builder.Build().Run();

public static class TracingExtensions {
    
    public static IResourceBuilder<T> WithTracing<T>(this IResourceBuilder<T> builder, string? appInsightsConnectionString) where T : Aspire.Hosting.ApplicationModel.IResourceWithEnvironment
    {
        if (! string.IsNullOrEmpty(appInsightsConnectionString))
        {
            return builder.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", appInsightsConnectionString);
        }
        return builder.WithEnvironment("OTEL_PYTHON_CONFIGURATOR", "configurator")
                            .WithEnvironment("OTEL_PYTHON_DISTRO", "not_azure");
    }
}
