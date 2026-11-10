using System.Text.Json;
using Cica.Agent.Service;
using Xunit;

namespace Cica.Agent.Tests;

public sealed class AgentCollectionGateTests
{
    [Theory]
    [InlineData("{}", true)]
    [InlineData("{\"collection_enabled\":true}", true)]
    [InlineData("{\"collection_enabled\":false}", false)]
    public void CollectionRequiresActivationWhenBackendProvidesTheGate(string json, bool expected)
    {
        using JsonDocument document = JsonDocument.Parse(json);
        Assert.Equal(expected, AgentCollectionGate.IsEnabled(document.RootElement));
    }

    [Theory]
    [InlineData("null")]
    [InlineData("0")]
    [InlineData("\"true\"")]
    [InlineData("{}")]
    [InlineData("[]")]
    public void MalformedAuthorizationCannotEnableCollection(string value)
    {
        using JsonDocument document = JsonDocument.Parse("{\"collection_enabled\":" + value + "}");
        Assert.Throws<InvalidDataException>(() => AgentCollectionGate.IsEnabled(document.RootElement));
    }
}
