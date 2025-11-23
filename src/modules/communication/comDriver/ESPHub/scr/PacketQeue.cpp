#include "PacketQueue.h"

PacketQueue::PacketQueue(size_t max_size) : max_size_(max_size) {}

// Adiciona um pacote ao buffer
bool PacketQueue::push(const PFOXPacket& packet) {
    if (queue_.size() >= max_size_) {
        // Fila cheia, pacote descartado
        return false;
    }
    queue_.push(packet);
    return true;
}

// Remove o pacote mais antigo da fila
bool PacketQueue::pop(PFOXPacket& packet) {
    if (queue_.empty()) {
        return false;
    }
    packet = queue_.front();
    queue_.pop();
    return true;
}

// Retorna o tamanho atual da fila
size_t PacketQueue::size() const {
    return queue_.size();
}

// Verifica se a fila está vazia
bool PacketQueue::isEmpty() const {
    return queue_.empty();
}

// Verifica se a fila está cheia
bool PacketQueue::isFull() const {
    return queue_.size() >= max_size_;
}
