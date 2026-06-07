import hashlib
import math
from typing import List

class HyperLogLog:
    def __init__(self, p: int = 14):
        self.p = p
        self.m = 1 << p
        self.registers = [0] * self.m
        self.alpha = self._get_alpha()

    def _get_alpha(self) -> float:
        if self.m == 16: return 0.673
        if self.m == 32: return 0.697
        if self.m == 64: return 0.709
        return 0.7213 / (1 + 1.079 / self.m)

    def _hash(self, value: str) -> int:
        return int(hashlib.sha256(value.encode()).hexdigest(), 16)

    def add(self, value: str):
        h = self._hash(value)
        register_index = h & (self.m - 1)
        w = h >> self.p
        rank = 1
        for i in range(64 - self.p):
            if (w >> i) & 1:
                break
            rank += 1
            
        self.registers[register_index] = max(self.registers[register_index], rank)

    def count(self) -> int:
        estimate = self.alpha * (self.m ** 2) / sum([2 ** -x for x in self.registers])
        
        if estimate <= 2.5 * self.m:
            zeros = self.registers.count(0)
            if zeros != 0:
                estimate = self.m * math.log(self.m / zeros)
                
        return int(estimate)

    def merge(self, other: 'HyperLogLog'):
        if self.p != other.p:
            raise ValueError("Cannot merge HLLs with different precision")
        for i in range(self.m):
            self.registers[i] = max(self.registers[i], other.registers[i])