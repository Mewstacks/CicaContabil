using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Regaro.Agent.Service;

Host.CreateDefaultBuilder(args)
    .UseWindowsService(options => options.ServiceName = "Regaro Agent")
    .ConfigureServices(services => services.AddHostedService<Worker>())
    .Build()
    .Run();
