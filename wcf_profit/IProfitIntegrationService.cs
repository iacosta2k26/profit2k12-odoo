using System;
using System.ServiceModel;

namespace ProfitWcfService
{
    [ServiceContract]
    public interface IProfitIntegrationService
    {
        [OperationContract]
        ProfitResponse ProcesarFactura(PosOrderPayload payload);

        [OperationContract]
        ProfitResponse CrearNotaCredito(PosOrderPayload payload);
        
        [OperationContract]
        ProfitResponse SincronizarCierreTurno(SessionSummary payload);
    }

    [DataContract]
    public class ProfitResponse
    {
        [DataMember]
        public bool Success { get; set; }
        
        [DataMember]
        public string ProfitDocumentNumber { get; set; }
        
        [DataMember]
        public string ErrorMessage { get; set; }
    }
}
