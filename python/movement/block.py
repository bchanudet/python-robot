import time
from enum import Enum

class MovementBlockType(Enum):
    """Movement Block type"""
    Still = 0
    Forward = 10        # Forward
    Forwardx2 = 11
    Forwardx4 = 12
    Reverse = 20        # Reverse
    Reversex2 = 21
    Reversex4 = 22
    TurnLeft45 = 31     # Turn by the left
    TurnLeft90 = 32
    TurnLeft180 = 33
    TurnRight45 = 41    # Turn by the right
    TurnRight90 = 42
    TurnRight180 = 43

class MovementBlock(object):
    """Represents a constructed movement of an undetermined duration"""
    def __init__(self, block_type: MovementBlockType = MovementBlockType.Still):
        self.type = MovementBlockType.Still
        self.set_type(block_type)

    def set_type(self, block_type: MovementBlockType = MovementBlockType.Still):
        """Set the block type"""
        self.type = block_type

    def run(self):
        """Run the block movement"""
        # Executes the queue
        if self.type == MovementBlockType.Forward:
            time.sleep(1)
        time.sleep(1)


class MovementBlockQueue(object):
    """Represent a queue of movement blocks"""
    def __init__(self):
        self.blocks = list()

    def add_to_queue(self, new_block: MovementBlock):
        """Add a new block to the queue"""
        self.blocks.append(new_block)

    def run_queue(self):
        """Run the queue"""
        for block in self.blocks:
            block.run()
        return True
