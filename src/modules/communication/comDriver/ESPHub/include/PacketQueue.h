#pragma once
#include "PFOXPacket.h"
#include <vector>

class PacketQueue {
private:
    std::vector<PFOXPacket> queue;
    size_t max_size;
public:
    PacketQueue(size_t max = 50) : max_size(max) {}
    bool push(const PFOXPacket& pkt);
    bool pop(PFOXPacket& pkt);
    size_t size() const { return queue.size(); }
};
