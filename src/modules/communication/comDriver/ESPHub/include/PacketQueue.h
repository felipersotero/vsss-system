// PacketQueue.h

#pragma once
#include "PFOXPacket.h"
#include <queue> // NOVO: Incluir a biblioteca de fila otimizada

class PacketQueue {
private:
    // TROCA: Usar std::queue para operações O(1)
    std::queue<PFOXPacket> queue; 
    size_t max_size;
public:
    PacketQueue(size_t max = 50) : max_size(max) {}
    bool push(const PFOXPacket& pkt);
    bool pop(PFOXPacket& pkt);
    size_t size() const { return queue.size(); }
    
    // Adicione os métodos auxiliares, caso não estejam explícitos no .cpp
    bool isEmpty() const { return queue.empty(); }
    bool isFull() const { return queue.size() >= max_size; }
};