from typing import List
from logger import LogLevel, Logger


class CommandProcessingManager:
    def __init__(self, verbose: bool = False):
        self.completed_commands: List[CommandProcessing] = []
        self.active_commands: List[CommandProcessing] = []
        self.current_tick = 0
        self.verbose = verbose

    def vprint(self, level: LogLevel = LogLevel.INFO, *args, **kwargs):
        if self.verbose:
            Logger.log(level, *args, **kwargs)

    def set_tick(self, tick: int):
        self.current_tick = tick

    def new_fetch(self, address: int, id: int):
        command = CommandProcessing(self, address, id)
        command.fetch(self.current_tick)
        self.active_commands.append(command)

    def _find_command(self, address: int, id: int):
        for command in self.active_commands:
            if command.address == address and command.id == id:
                return command
        
        self.vprint(LogLevel.WARNING, f"Command not found <pc={hex(address) if address else 'None'}, id={id}>. Active commands: {[f'<pc={hex(cmd.address)}, id={cmd.id}>' for cmd in self.active_commands]}")
        return None

    def dispatching_complete(self, address: int, id: int, instruction: int):
        command = self._find_command(address, id)
        if not command:
            self.vprint(LogLevel.WARNING, f"Tried to dispatch command <pc={hex(address)}, id={id}>, but not found it!")
            return
                
        command.dispatch(self.current_tick, instruction)

    def decoding(self, address: int, id: int, wait: bool):
        command = self._find_command(address, id)
        if not command:
            self.vprint(LogLevel.WARNING, f"Tried to decode command <pc={hex(address)}, id={id}>, but not found it!")
            return

        command.decode(self.current_tick, wait)

    def issue_conflict(self, address: int, id: int):
        command = self._find_command(address, id)
        if not command:
            self.vprint(LogLevel.WARNING, f"Cannot issue conflict for non-existent command <pc={hex(address) if address else 'None'}, id={id}>")
            return

        command.issue_conflict(self.current_tick)

    def issue_bu(self, address: int, id: int):
        command = self._find_command(address, id)
        if not command:
            self.vprint(LogLevel.WARNING, f"Cannot issue BU for non-existent command <pc={hex(address) if address else 'None'}, id={id}>")
            return

        command.issue_bu(self.current_tick)
        self.completed_commands.append(self.active_commands.pop(self.active_commands.index(command)))

    def issue_alu(self, address: int, id: int):
        command = self._find_command(address, id)
        if not command:
            self.vprint(LogLevel.WARNING, f"Tried to issue_alu command <pc={hex(address)}, id={id}>, but not found it!")
            return

        command.issue_alu(self.current_tick)
        self.completed_commands.append(self.active_commands.pop(self.active_commands.index(command)))

    def issue_lsu(self, address: int, id: int):
        command = self._find_command(address, id)
        if not command:
            self.vprint(LogLevel.WARNING, f"Cannot issue LSU for non-existent command <pc={hex(address) if address else 'None'}, id={id}>")
            return

        command.issue_lsu(self.current_tick)
        self.completed_commands.append(self.active_commands.pop(self.active_commands.index(command)))

    def flush(self):
        for command in self.active_commands:
            command.cancel(self.current_tick)
        self.completed_commands.extend(self.active_commands)
        self.active_commands.clear()
        self.vprint(LogLevel.DEBUG, "flush detected")
        
    def postprocess(self) -> list:
        processed_commands = []
        wx_sequence_count = 0
        
        for cmd in self.completed_commands:
            if not cmd.history:
                processed_commands.append(cmd)
                continue
                
            ticks = sorted(cmd.history.keys())
            full_history = {
                tick: cmd.history.get(tick, "C") 
                for tick in range(min(ticks), max(ticks) + 1)
            }
            
            # FX - reset wx sequence
            if any("FX" in str(state) for state in full_history.values()):
                wx_sequence_count = 0
            
            new_history = {}
            sorted_ticks = sorted(full_history.keys())
            
            for i, tick in enumerate(sorted_ticks):
                current = full_history[tick]
                new_state = current
                
                # W before "AL", "M1", "M2", "M3", "C", "B" -> D
                if current == "W" and i + 1 < len(sorted_ticks):
                    next_state = full_history[sorted_ticks[i + 1]]
                    if next_state in ["AL", "M1", "M2", "M3", "C", "B"]:
                        new_state = "D"
                
                if i + 1 < len(sorted_ticks):
                    next_tick = sorted_ticks[i + 1]
                    next_state = full_history[next_tick]
                    
                    if next_state == "X":
                        if current == "W":
                            if wx_sequence_count == 0:
                                # W before X -> D (1)
                                new_state = "D"
                                wx_sequence_count = 1
                            elif wx_sequence_count == 1:
                                # W before X after (1) X -> DX
                                full_history[next_tick] = "DX"
                                wx_sequence_count = 2
                        elif wx_sequence_count == 1:
                            # after (1) X -> DX
                            full_history[next_tick] = "DX"
                            wx_sequence_count = 2
                
                new_history[tick] = new_state
            
            processed_cmd = CommandProcessing(self, cmd.address, cmd.id)
            processed_cmd.instruction = cmd.instruction
            processed_cmd.stage = cmd.stage
            processed_cmd.history = new_history
            processed_commands.append(processed_cmd)
        
        return processed_commands


class CommandProcessing:
    def __init__(self, manager: CommandProcessingManager, address: int, id: int):
        self.address = address
        self.instruction: int = 0
        self.id = id
        self.stage = "fetching"
        self.history = {}
        self.manager = manager

    def vprint(self, *args, **kwargs):
        self.manager.vprint(*args, **kwargs)

    def _fill_wait_gap(self, tick):
        for t in range(max(self.history.keys()) + 1, tick):
            self.history[t] = "W"

    def cancel(self, tick):
        self._fill_wait_gap(tick)

        if tick in self.history.keys() and (self.history[tick] == "D" or self.history[tick] == "F"):
            self.history[tick] += "X"
        else:
            self.history[tick] = "X"
        self.stage = "canceled"
        
        self.vprint(LogLevel.DEBUG, f"Command canceled: pc={hex(self.address)}, id={self.id}")

    def fetch(self, tick):
        if self.stage != "fetching":
            self.vprint(LogLevel.WARNING, f"Wrong time fetch for command {self}")
        else:
            self.stage = "dispatching"
            self.history[tick] = "F"
            
        self.vprint(LogLevel.DEBUG, f"New fetch: pc={hex(self.address) if self.address else 'None'}, id={self.id}")

    def dispatch(self, tick, instruction):
        if self.stage != "dispatching":
            self.vprint(LogLevel.WARNING, f"Wrong time dispatch for command {self}")
        else:
            self.stage = "decoding"
            self.history[tick] = "ID"
            self.instruction = instruction
            
        self.vprint(LogLevel.DEBUG, f"Dispatching complete: pc={hex(self.address)}, id={self.id}")

    def decode(self, tick, wait):
        if self.stage != "decoding":
            self.vprint(LogLevel.WARNING, f"Wrong time decode for command {self}")
        else:
            self._fill_wait_gap(tick)
            if wait:
                self.history[tick] = "W"
            else:
                self.stage = "issuing"
                self.history[tick] = "D"
                
        self.vprint(LogLevel.DEBUG, f"Decoding: pc={hex(self.address)}, id={self.id}, wait={wait}")

    def issue_conflict(self, tick):
        if self.stage != "issuing":
            self.vprint(LogLevel.WARNING, f"Wrong time issue_conflict for command {self}")
        else:
            self.history[tick] = "C"
            
        self.vprint(LogLevel.DEBUG, f"Conflict detected for pc={hex(self.address)}, id={self.id}")

    def _issue(self):
        if self.stage != "issuing":
            self.vprint(LogLevel.WARNING, f"Wrong time issue for command {self}")
        else:
            self.stage = "complete"

    def issue_bu(self, tick):
        self._issue()
        self.history[tick] = "B"
        
        self.vprint(LogLevel.DEBUG, f"BU issue: pc={hex(self.address)}, id={self.id}")

    def issue_alu(self, tick):
        self._issue()
        self.history[tick] = "AL"
        
        self.vprint(LogLevel.DEBUG, f"ALU issue: pc={hex(self.address)}, id={self.id}")

    def issue_lsu(self, tick):
        self._issue()
        self.history[tick] = "M1"
        self.history[tick + 1] = "M2"
        self.history[tick + 2] = "M3"
        
        self.vprint(LogLevel.DEBUG, f"LSU issue: pc={hex(self.address)}, id={self.id}")

    def __str__(self):
        return f"<Command pc={hex(self.address)}, id={self.id}, history={self.history}>"