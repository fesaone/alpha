import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class StreamPacket:
    stream_id: str
    seq: int
    payload: bytes
    checksum: str
    is_fin: bool = False

class Multiplexor:
    def __init__(self, chunk_size: int = 64):
        self.chunk_size = chunk_size
        self.stream_buffer: Dict[str, Dict[int, bytes]] = {}
        self.received_meta: Dict[str, int] = {}

    def _hash_chunk(self, data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    def fragment(self, stream_id: str, data: bytes) -> List[StreamPacket]:
        packets = []
        chunks = [data[i:i+self.chunk_size] for i in range(0, len(data), self.chunk_size)]
        
        for seq, chunk in enumerate(chunks):
            is_fin = seq == len(chunks) - 1
            packets.append(StreamPacket(
                stream_id=stream_id, seq=seq, payload=chunk,
                checksum=self._hash_chunk(chunk), is_fin=is_fin
            ))
        return packets

    def reassemble(self, packet: StreamPacket) -> bytes:
        if packet.stream_id not in self.stream_buffer:
            self.stream_buffer[packet.stream_id] = {}
            self.received_meta[packet.stream_id] = 0

        if self._hash_chunk(packet.payload) != packet.checksum:
            raise IOError(f"Checksum mismatch on stream {packet.stream_id} seq {packet.seq}")

        self.stream_buffer[packet.stream_id][packet.seq] = packet.payload
        self.received_meta[packet.stream_id] += 1

        if packet.is_fin:
            ordered_payload = b''.join(
                self.stream_buffer[packet.stream_id][seq] 
                for seq in sorted(self.stream_buffer[packet.stream_id].keys())
            )
            del self.stream_buffer[packet.stream_id]
            del self.received_meta[packet.stream_id]
            return ordered_payload

        return b''