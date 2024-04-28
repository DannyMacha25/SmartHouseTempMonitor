// See https://aka.ms/new-console-template for more information
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

class IOTParameters
{
    public int device_id {get; set;}
    public Socket Client {get; set;}
}

class Program
{

    static void Main(string[] args)
    {
        Console.WriteLine("Server Started!");

        IPHostEntry ipHost = Dns.GetHostEntry(Dns.GetHostName());
        IPAddress ipAddr = ipHost.AddressList[3];
        IPAddress ip = System.Net.IPAddress.Parse("192.168.0.28");

        IPEndPoint ipEndPoint = new IPEndPoint(ip, 1024);

        using Socket listener = new(ipEndPoint.AddressFamily,
        SocketType.Stream,
        ProtocolType.Tcp);

        listener.Bind(ipEndPoint);
        listener.Listen(1024);

        Console.WriteLine($"{ip}:1024");

        //var handler = await listener.AcceptAsync();

        while (true) {
            var buffer = new byte[1_024];
            //var received = await handler.ReceiveAsync(buffer, SocketFlags.None);
            //var response = Encoding.UTF8.GetString(buffer, 0, received);
            //Console.WriteLine($"{response}");
            
            while (true) {
                Console.WriteLine("Waiting for connection...");

                Socket client = listener.Accept();

                // Do initial check to see what kind of device this is
                byte[] bytes = new byte[1024];
                string data = new string("");
                int numBytes = client.Receive(bytes);
                data += Encoding.ASCII.GetString(bytes, 0, numBytes);

                // Get device type and spin up approp
                char device_type = data[0];

                switch(device_type) {
                    case 'p': // pico
                        IOTParameters iOT = new IOTParameters();
                        iOT.device_id = int.Parse(data.Substring(2));
                        iOT.Client = client;
                        Thread clientThread = new Thread(new ParameterizedThreadStart(HandleIOTDevice));
                        clientThread.Start(iOT);
                    break;

                    default:
                        Console.WriteLine("Unknown Device, stopping connection...");
                        client.Close();
                    break;
                }
                
            }

        }
    }

    static void HandleIOTDevice(object? param) {
        // If client is null, for some reason, just cut the thread
        if (param == null) {
            return;
        }

        IOTParameters parameters = (IOTParameters)param;

        Socket clientSocket = parameters.Client;
        Console.WriteLine(String.Format("Data Collector id:{0}", parameters.device_id));

        byte[] bytes = new byte[1024];
        string data = new string("");

        while (true) {
            int numBytes = clientSocket.Receive(bytes);

            if ( numBytes == 0) { // No data recieved, continue
                continue;
            }
            data += Encoding.ASCII.GetString(bytes, 0, numBytes);
            
            if (data[0] == 't') {
                float temp = float.Parse(data.Substring(2));
                Console.WriteLine(String.Format("Temp from Device {0}: {1}", parameters.device_id, temp));
            }

            data = new string("");
            if(data.IndexOf("<EOF>") > -1) 
                break;
        }

        Console.WriteLine("Connection with client closed");
        clientSocket.Close();
    }
}

