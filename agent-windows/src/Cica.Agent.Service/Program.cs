using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Cica.Agent.Service;

Host.CreateDefaultBuilder(args)
    .UseWindowsService(options => options.ServiceName = "CICA Agent")
    .ConfigureServices(services => services.AddHostedService<Worker>())
    .Build()
    .Run();
