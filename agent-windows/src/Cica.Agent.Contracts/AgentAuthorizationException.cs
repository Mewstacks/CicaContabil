namespace Cica.Agent.Service;

internal sealed class AgentAuthorizationException : Exception
{
    internal AgentAuthorizationException()
        : base("O servidor CICA recusou a autorização deste agente.") { }
}
