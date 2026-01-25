//+------------------------------------------------------------------+
//| ProtobufSerializer.mqh                                            |
//| Lightweight Protobuf Wire Format Encoder for MQL5                |
//| Copyright 2026-01-25                                             |
//+------------------------------------------------------------------+
//| Implements Protocol Buffers wire format encoding                 |
//| Reference: https://protobuf.dev/programming-guides/encoding/     |
//+------------------------------------------------------------------+

#property copyright "EA Sync - Fintech Systems Architect"
#property link      "https://easync.com"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Wire Types (Protobuf encoding)                                   |
//+------------------------------------------------------------------+
enum WIRE_TYPE
{
    WIRE_VARINT = 0,           // int32, int64, uint32, uint64, bool, enum
    WIRE_64BIT = 1,            // fixed64, sfixed64, double
    WIRE_LENGTH_DELIMITED = 2, // string, bytes, embedded messages
    WIRE_32BIT = 5             // fixed32, sfixed32, float
};

//+------------------------------------------------------------------+
//| Union for Double to Bytes conversion (MQL5 compatible)          |
//+------------------------------------------------------------------+
union DoubleToLong
{
    double d;
    long   l;
};

//+------------------------------------------------------------------+
//| Protobuf Serializer Class                                        |
//+------------------------------------------------------------------+
class CProtobufSerializer
{
private:
    uchar m_buffer[];          // Output buffer
    int   m_position;          // Current write position
    
    void WriteVarint(ulong value);
    void WriteTag(int field_number, WIRE_TYPE wire_type);
    void WriteRawBytes(const uchar &data[], int size);
    
public:
    CProtobufSerializer();
    ~CProtobufSerializer();
    
    void WriteString(int field_number, string value);
    void WriteInt64(int field_number, long value);
    void WriteDouble(int field_number, double value);
    void WriteInt32(int field_number, int value);
    
    void GetBytes(uchar &output[]);
    int  GetSize() const { return m_position; }
    void Reset();
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CProtobufSerializer::CProtobufSerializer()
{
    ArrayResize(m_buffer, 1024);
    m_position = 0;
}

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CProtobufSerializer::~CProtobufSerializer()
{
    ArrayFree(m_buffer);
}

//+------------------------------------------------------------------+
//| Reset buffer                                                     |
//+------------------------------------------------------------------+
void CProtobufSerializer::Reset()
{
    m_position = 0;
}

//+------------------------------------------------------------------+
//| Write Varint (variable-length integer)                           |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteVarint(ulong value)
{
    while(value >= 0x80)
    {
        if(m_position >= ArraySize(m_buffer))
            ArrayResize(m_buffer, ArraySize(m_buffer) * 2);
        
        m_buffer[m_position++] = (uchar)((value & 0x7F) | 0x80);
        value >>= 7;
    }
    
    if(m_position >= ArraySize(m_buffer))
        ArrayResize(m_buffer, ArraySize(m_buffer) * 2);
    
    m_buffer[m_position++] = (uchar)value;
}

//+------------------------------------------------------------------+
//| Write Field Tag                                                  |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteTag(int field_number, WIRE_TYPE wire_type)
{
    ulong tag = (ulong)((field_number << 3) | wire_type);
    WriteVarint(tag);
}

//+------------------------------------------------------------------+
//| Write raw bytes                                                  |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteRawBytes(const uchar &data[], int size)
{
    while(m_position + size >= ArraySize(m_buffer))
        ArrayResize(m_buffer, ArraySize(m_buffer) * 2);
    
    ArrayCopy(m_buffer, data, m_position, 0, size);
    m_position += size;
}

//+------------------------------------------------------------------+
//| Write String Field                                               |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteString(int field_number, string value)
{
    WriteTag(field_number, WIRE_LENGTH_DELIMITED);
    
    uchar str_bytes[];
    int byte_count = StringToCharArray(value, str_bytes, 0, WHOLE_ARRAY, CP_UTF8);
    
    if(byte_count > 0 && str_bytes[byte_count - 1] == 0)
        byte_count--;
    
    WriteVarint((ulong)byte_count);
    
    if(byte_count > 0)
        WriteRawBytes(str_bytes, byte_count);
}

//+------------------------------------------------------------------+
//| Write Int64 Field                                                |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteInt64(int field_number, long value)
{
    WriteTag(field_number, WIRE_VARINT);
    WriteVarint((ulong)value);
}

//+------------------------------------------------------------------+
//| Write Int32 Field                                                |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteInt32(int field_number, int value)
{
    WriteTag(field_number, WIRE_VARINT);
    WriteVarint((ulong)value);
}

//+------------------------------------------------------------------+
//| Write Double Field (IEEE 754 little-endian)                      |
//+------------------------------------------------------------------+
void CProtobufSerializer::WriteDouble(int field_number, double value)
{
    WriteTag(field_number, WIRE_64BIT);
    
    // Use union to convert double to its binary representation
    DoubleToLong converter;
    converter.d = value;
    long bits = converter.l;
    
    uchar double_bytes[8];
    for(int i = 0; i < 8; i++)
        double_bytes[i] = (uchar)((bits >> (i * 8)) & 0xFF);
    
    WriteRawBytes(double_bytes, 8);
}

//+------------------------------------------------------------------+
//| Get serialized bytes                                             |
//+------------------------------------------------------------------+
void CProtobufSerializer::GetBytes(uchar &output[])
{
    ArrayResize(output, m_position);
    ArrayCopy(output, m_buffer, 0, 0, m_position);
}

//+------------------------------------------------------------------+