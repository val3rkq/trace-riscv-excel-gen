import argparse
import traceback
from pathlib import Path
from parser import parse
from convert import to_int
from export import export_to_xlsx, export_to_csv
from processor import CommandProcessingManager
from logger import LogLevel, Logger


def average_signal_data_by_tick(data: dict) -> list:
    data_index_by_cyc_cnt = {}
    
    for index, cyc_cnt in enumerate(data["/tb/cyc_cnt"]):
        try:
            if "'h" in cyc_cnt:
                hex_value = cyc_cnt.split("'h")[1]
                if 'x' not in hex_value and hex_value:
                    tick = int(hex_value, 16)
                    data_index_by_cyc_cnt.setdefault(tick, []).append(index)
        except (ValueError, IndexError):
            continue
    
    return [
        (cyc_cnt, index_list[len(index_list) // 2])
        for cyc_cnt, index_list in sorted(data_index_by_cyc_cnt.items())
    ]


def generate(input_path: Path, verbose: bool = False) -> tuple[int, list]:
    def to_hex(data) -> "str | None":
        return hex(data) if data is not None else None
    
    data = parse(input_path)
    data_by_tick = average_signal_data_by_tick(data)
    manager = CommandProcessingManager(verbose=verbose)

    for cyc_cnt, index in data_by_tick:
        manager.set_tick(cyc_cnt)
        
        get = lambda name: data[name][index]
        get_int = lambda name, base=16: to_int(get(name), base)
        
        current_cyc_cnt = get_int("/tb/cyc_cnt")
        manager.vprint(LogLevel.INFO, f"Tick: {current_cyc_cnt}")

        # Fetching
        manager.vprint(LogLevel.INFO, f"FETCHING")
        pc = get_int("/tb/uut/cpu/fetch_block/pc")
        pc_id = get_int("/tb/uut/cpu/id_block/pc_id")
        manager.vprint(LogLevel.DEBUG, f"PC: {to_hex(pc)}, pc_id: {pc_id}")

        if get_int("/tb/uut/cpu/fetch_block/pc_id_assigned") == 1:
            manager.new_fetch(pc, pc_id)

        # ID (Dispatch)
        manager.vprint(LogLevel.INFO, f"DISPATCH")
        pc_table = [to_int(pc_val) for pc_val in get("/tb/uut/cpu/id_block/pc_table")]
        if get_int("/tb/uut/cpu/fetch_block/fetch_complete") == 1:
            dispatching_id = (pc_id - 1) % 8
            dispatching_pc = pc_table[dispatching_id]
            fetch_instruction = get_int("/tb/uut/cpu/fetch_block/fetch_instruction")
            manager.dispatching_complete(dispatching_pc, dispatching_id, fetch_instruction)

        # Decode
        manager.vprint(LogLevel.INFO, f"DECODE")
        decode = get("/tb/uut/cpu/id_block/decode")
        decode_id, decode_pc = to_int(decode[0]), to_int(decode[1])
        decode_valid = to_int(decode[3]) == 1
        decode_addr_valid = to_int(decode[4]) == 1
        
        if decode_valid and decode_addr_valid and pc_table[decode_id] == decode_pc:
            decode_advance = get("/tb/uut/cpu/id_block/decode_advance") == "St1"
            manager.vprint(LogLevel.DEBUG, f"decode_pc: {to_hex(decode_pc)}")
            manager.decoding(decode_pc, decode_id, wait=not decode_advance)

        # Issue
        manager.vprint(LogLevel.INFO, f"ISSUE")
        issue = get("/tb/uut/cpu/decode_and_issue_block/issue")
        issue_pc, issue_id = to_int(issue[0]), to_int(issue[9])
        
        if to_int(issue[10]) == 1:  # issue_stage_valid
            manager.vprint(LogLevel.DEBUG, f"issue.pc: {to_hex(issue_pc)}, issue.id: {issue_id}")
            
            requests = [
                get_int("/tb/uut/cpu/decode_and_issue_block/unit_issue[0]/new_request") == 1,  # ALU
                get_int("/tb/uut/cpu/decode_and_issue_block/unit_issue[1]/new_request") == 1,  # LSU  
                get_int("/tb/uut/cpu/decode_and_issue_block/unit_issue[2]/new_request") == 1,  # BU
            ]
            
            manager.vprint(LogLevel.DEBUG, f"new_requests: ALU={requests[0]}, LSU={requests[1]}, BU={requests[2]}")

            if not any(requests):
                rs_conflict = get("/tb/uut/cpu/decode_and_issue_block/rs1_conflict") or get("/tb/uut/cpu/decode_and_issue_block/rs2_conflict")
                assert rs_conflict
                manager.issue_conflict(issue_pc, issue_id)
            else:
                issue_handlers = {
                    0: manager.issue_alu,  # ALU
                    1: manager.issue_lsu,  # LSU
                    2: manager.issue_bu,   # BU
                }
                for i, requested in enumerate(requests):
                    if requested:
                        handler = issue_handlers[i]
                        handler(issue_pc, issue_id)
                        break

        # Flush
        manager.vprint(LogLevel.INFO, f"FLUSH")
        if get_int("/tb/uut/cpu/gc_unit_block/gc_fetch_flush") == 1:
            manager.flush()

        manager.vprint(LogLevel.DEBUG, f"Active commands: {len(manager.active_commands)}")
        for cmd in manager.active_commands:
            manager.vprint(LogLevel.DEBUG, f"  - {cmd}")
        manager.vprint(LogLevel.DEBUG)
    return len(data_by_tick), manager.postprocess()


def main():
    parser = argparse.ArgumentParser(description='Generate pipeline visualization')
    parser.add_argument('input_file', help='Input data file')
    parser.add_argument('output_file', nargs='?', help='Output file (optional)')
    parser.add_argument('--excel', action='store_true', help='Export to Excel format')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.is_file():
        Logger.critical(f"Input file not found: {input_path}")
        return
    
    if input_path.suffix.lower() != '.lst':
        Logger.critical(f"Input file must be .lst format, got: {input_path.suffix}")
        return
    
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        base_name = input_path.stem
        extension = ".xlsx" if args.excel else ".csv"
        output_path = Path(f"{base_name}{extension}")
    
    try:    
        ticks, completed_commands = generate(input_path, args.verbose)
        if args.excel:
            export_to_xlsx(completed_commands, ticks, output_path)
            Logger.info(f"Exported to Excel: {output_path}")
        else:
            export_to_csv(completed_commands, ticks, output_path)
            Logger.info(f"Exported to CSV: {output_path}")
    except Exception as e:
        Logger.error(f"Error during pipeline generation: {e}")
        Logger.error(f"Error type: {type(e).__name__}")
        if args.verbose:
            Logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == '__main__':
    main()