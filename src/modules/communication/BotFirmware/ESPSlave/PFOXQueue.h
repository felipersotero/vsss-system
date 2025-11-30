#ifndef PACKETQUEUE_H
#define PACKETQUEUE_H

#include <queue>
#include "PFOXPacket.h"

class PacketQueue {
public:
    PacketQueue(size_t max = 1024);

    bool push(const PFOXPacket& packet);
    bool pop(PFOXPacket& pkt);

    size_t size() const;
    bool isEmpty() const;
    bool isFull() const;

private:
    size_t max_size;
    std::queue<PFOXPacket> queue;
};

#endif
