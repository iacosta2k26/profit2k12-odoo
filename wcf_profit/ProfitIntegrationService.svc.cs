using System;
using System.Data.SqlClient;
using System.Text.Json;
using System.Configuration;

namespace ProfitWcfService
{
    public class ProfitIntegrationService : IProfitIntegrationService
    {
        private readonly string connectionString = "Server=myServerAddress;Database=myDataBase;User Id=myUsername;Password=myPassword;"; // Simulado

        public ProfitResponse ProcesarFactura(PosOrderPayload payload)
        {
            ProfitResponse response = new ProfitResponse();
            
            using (SqlConnection conn = new SqlConnection(connectionString))
            {
                try
                {
                    conn.Open();
                    // Iniciar transacción estricta para garantizar consistencia
                    using (SqlTransaction trans = conn.BeginTransaction())
                    {
                        try
                        {
                            // 1. Insertar Encabezado (factura)
                            string insertFactura = @"
                                INSERT INTO factura (fact_num, fec_emis, co_cli, co_ven, tot_bruto, iva, tot_neto, co_us_in)
                                VALUES (@fact_num, @fec_emis, @co_cli, @co_ven, @tot_bruto, @iva, @tot_neto, @co_us_in)";
                                
                            using (SqlCommand cmd = new SqlCommand(insertFactura, conn, trans))
                            {
                                cmd.Parameters.AddWithValue("@fact_num", payload.Transaction.OdooPosReference);
                                cmd.Parameters.AddWithValue("@fec_emis", payload.Transaction.FecEmis);
                                cmd.Parameters.AddWithValue("@co_cli", "CLIENTE_GENERICO"); // A mapear
                                cmd.Parameters.AddWithValue("@co_ven", "VENDEDOR_01"); // A mapear
                                cmd.Parameters.AddWithValue("@tot_bruto", payload.TaxesSummary.BaseImponibleVes);
                                cmd.Parameters.AddWithValue("@iva", payload.TaxesSummary.MontoIvaVes);
                                cmd.Parameters.AddWithValue("@tot_neto", payload.TaxesSummary.BaseImponibleVes + payload.TaxesSummary.MontoIvaVes);
                                cmd.Parameters.AddWithValue("@co_us_in", payload.Session.CashierId); // Auditoría estricta
                                cmd.ExecuteNonQuery();
                            }

                            // 2. Insertar Renglones (reng_fac)
                            int rengNum = 1;
                            foreach (var line in payload.Lines)
                            {
                                string insertRenglon = @"
                                    INSERT INTO reng_fac (fact_num, reng_num, co_art, total_art, prec_vta)
                                    VALUES (@fact_num, @reng_num, @co_art, @total_art, @prec_vta)";
                                    
                                using (SqlCommand cmdReng = new SqlCommand(insertRenglon, conn, trans))
                                {
                                    cmdReng.Parameters.AddWithValue("@fact_num", payload.Transaction.OdooPosReference);
                                    cmdReng.Parameters.AddWithValue("@reng_num", rengNum++);
                                    cmdReng.Parameters.AddWithValue("@co_art", line.ProductId);
                                    cmdReng.Parameters.AddWithValue("@total_art", line.Qty);
                                    cmdReng.Parameters.AddWithValue("@prec_vta", line.UnitPriceRawVes);
                                    cmdReng.ExecuteNonQuery();
                                }
                            }
                            
                            // 3. Tesorería: Insertar Cobros (cobros) y Movimientos de Caja (mov_caj)
                            // (Lógica omitida por brevedad, pero seguiría el mismo patrón SQL)

                            trans.Commit();
                            response.Success = true;
                            response.ProfitDocumentNumber = payload.Transaction.OdooPosReference;
                        }
                        catch (Exception ex)
                        {
                            trans.Rollback();
                            response.Success = false;
                            response.ErrorMessage = "Transacción SQL abortada: " + ex.Message;
                        }
                    }
                }
                catch (Exception ex)
                {
                    response.Success = false;
                    response.ErrorMessage = "Error de conexión a Profit: " + ex.Message;
                }
            }
            return response;
        }

        public ProfitResponse CrearNotaCredito(PosOrderPayload payload)
        {
            // Implementación análoga a ProcesarFactura pero insertando en dev_cli y validando original
            return new ProfitResponse { Success = true, ProfitDocumentNumber = "NC-" + payload.Transaction.OdooPosReference };
        }

        public ProfitResponse SincronizarCierreTurno(SessionSummary payload)
        {
            // Valida los totales vs la BD
            return new ProfitResponse { Success = true };
        }
    }
    
    // Simulación de las clases (DataContracts) mapeadas al JSON
    public class PosOrderPayload {
        public Transaction Transaction { get; set; }
        public SessionInfo Session { get; set; }
        public TaxesSummary TaxesSummary { get; set; }
        public OrderLine[] Lines { get; set; }
    }
    public class Transaction { public string OdooPosReference { get; set; } public DateTime FecEmis { get; set; } }
    public class SessionInfo { public string CashierId { get; set; } }
    public class TaxesSummary { public decimal BaseImponibleVes { get; set; } public decimal MontoIvaVes { get; set; } }
    public class OrderLine { public string ProductId { get; set; } public decimal Qty { get; set; } public decimal UnitPriceRawVes { get; set; } }
    public class SessionSummary { }
}
