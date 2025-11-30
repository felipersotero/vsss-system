#include "PFOXQueue.h"

PacketQueue::PacketQueue(size_t max_size) : max_size(max_size) {}

// Adiciona um pacote ao buffer
bool PacketQueue::push(const PFOXPacket& packet) {
    if (queue.size() >= max_size) {
        // Fila cheia, pacote descartado
        return false;
    }
    queue.push(packet);
    return true;
}

bool PacketQueue::pop(PFOXPacket& pkt) {
    if (queue.empty())
        return false;
        
    // 1. Copia o elemento do início
    pkt = queue.front();
    
    // 2. Remove o elemento do início (Operação O(1) e muito mais rápida)
    queue.pop(); 
    
    return true;
}

// Retorna o tamanho atual da fila
size_t PacketQueue::size() const {
    return queue.size();
}

// Verifica se a fila está vazia
bool PacketQueue::isEmpty() const {
    return queue.empty();
}

// Verifica se a fila está cheia
bool PacketQueue::isFull() const {
    return queue.size() >= max_size;
}
