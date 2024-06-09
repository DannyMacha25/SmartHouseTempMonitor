// See https://aka.ms/new-console-template for more information
using System.Collections.Specialized;
using System.Data;
using System.Data.Common;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using Microsoft.Data.Sqlite;

class IOTParameters
{
    public String device_id {get; set;}
    public Socket Client {get; set;}
    public DBAdapter db {get; set;}
}
class DBAdapter
{
    private SqliteConnection db;
    
    public DBAdapter(String source) 
    {
        db = new SqliteConnection($"Data source={source}");
        db.Open();
    }

    public void UploadTemp(String device_id, String date_time, float temp) 
    {
        SqliteCommand cmd = db.CreateCommand();
        cmd.CommandText = 
        @"
            Insert into Readings
            Values ($date_time, $device_id, $temp);
        ";
        cmd.Parameters.AddWithValue("$date_time", date_time);
        cmd.Parameters.AddWithValue("device_id", device_id);
        cmd.Parameters.AddWithValue("temp", temp);

        cmd.ExecuteNonQuery();
    }

    public void AddNewDevice(String device_id, String name) 
    {
        SqliteCommand cmd = db.CreateCommand();
        cmd.CommandText = 
        @"
            Insert into Devices
            Values ($device_id, $name);
        ";
        cmd.Parameters.AddWithValue("$device_id", device_id);
        cmd.Parameters.AddWithValue("$name", name);

        cmd.ExecuteNonQuery();
    }

    public bool DoesDeviceExist(String device_id) 
    {
        SqliteCommand cmd = db.CreateCommand();
        cmd.CommandText = 
        @"
            Select *
            From Devices
            Where device_id = $device_id 
        ";
        cmd.Parameters.AddWithValue("$device_id", device_id);

        SqliteDataReader reader = cmd.ExecuteReader();
        if(reader.Read()) 
        {
            return true;
        } else 
        {
            return false;
        }
    }

    ~DBAdapter() {
        db.Close();
    }
}
class Program
{

    static void Main(string[] args)
    {
        // Initialize Database Connection
        DBAdapter db = new DBAdapter("data.db");

        // Initalize Server
        Console.WriteLine("Server Started!");

        IPHostEntry ipHost = Dns.GetHostEntry(Dns.GetHostName());
        IPAddress ip = System.Net.IPAddress.Parse("192.168.50.173");

        IPEndPoint ipEndPoint = new IPEndPoint(ip, 1024);

        using Socket listener = new(ipEndPoint.AddressFamily,
            SocketType.Stream,
            ProtocolType.Tcp);
            
        // Start Server
        listener.Bind(ipEndPoint);
        listener.Listen(1024);

        Console.WriteLine($"{ip}:1024");

        // Main Server Thread
        while (true) {
            Console.WriteLine("Waiting for connection...");

            Socket client = listener.Accept(); // Wait for a new connection

            // Do initial check to see what kind of device this is
            byte[] bytes = new byte[1024];
            string data = new string("");
            int numBytes = client.Receive(bytes);
            data += Encoding.ASCII.GetString(bytes, 0, numBytes);

            // Get device type and spin up appropriate thread
            char device_type = data[0];

            switch(device_type) 
            {
                case 'p': // Pico IOT device
                    IOTParameters iOT = new IOTParameters();
                    iOT.device_id = data.Substring(2);
                    iOT.Client = client;
                    iOT.db = db;
                    Thread clientThread = new Thread(new ParameterizedThreadStart(HandleIOTDevice)); // New thread for IOT device
                    clientThread.Start(iOT);

                    // Check if device is in DB
                    if (!db.DoesDeviceExist(iOT.device_id.ToString())) 
                    {
                        db.AddNewDevice(iOT.device_id, "Temp");
                        Console.WriteLine("Device added");
                    } else
                    {
                        Console.WriteLine("Device already exists");  
                    }
                break;

                default:
                    Console.WriteLine("Unknown Device, stopping connection...");
                    client.Close();
                break;
            }
                

        }
    }

    static void HandleIOTDevice(object? param) {
        // If client is null, for some reason, just cut the thread
        if (param == null) {
            return;
        }

        IOTParameters parameters = (IOTParameters)param; // Cast object? to readable object

        Socket clientSocket = parameters.Client;
        DBAdapter db = parameters.db;
        Console.WriteLine(String.Format("Data Collector id: {0}", parameters.device_id));

        byte[] bytes = new byte[1024]; // byte buffer
        string data = new string(""); // string buffer
        
        DateTime time_since_upload = new DateTime(2000, 1, 1);
        float last_recorded_temp = 0;
        while (true) {
            int numBytes = clientSocket.Receive(bytes);

            if (numBytes == 0) { // No data recieved, continue
                continue;
            }
            data += Encoding.ASCII.GetString(bytes, 0, numBytes); // Bytes -> String
            
            if (data[0] == 't') {
                float temp = float.Parse(data.Substring(2)); // Read temp
                //Console.WriteLine(String.Format("Temp from Device {0}: {1}", parameters.device_id, temp));

                // If in good time, upload temp to the database
                DateTime now = DateTime.Now;
                if ((now - time_since_upload).TotalMinutes > 1 || Math.Abs(last_recorded_temp - temp) > 1) {
                    db.UploadTemp(parameters.device_id, now.ToString("yyyy-MM-dd HH:mm:ss"), temp);
                    Console.WriteLine($"Temp from {parameters.device_id} uploaded to db");
                    time_since_upload = now;
                    last_recorded_temp = temp;
                }
            }

            data = new string(""); // Reset string buffer

            if(data.IndexOf("<EOF>") > -1) 
                break;
        }

        Console.WriteLine("Connection with client closed");
        clientSocket.Close();
    }
}

