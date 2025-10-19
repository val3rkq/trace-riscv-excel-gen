from pathlib import Path
import csv
import xlsxwriter


def export_to_csv(completed_commands: list, tick_count: int, output_path: Path) -> None:
    with open(output_path, 'w', newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Адрес', 'Код', 'id'] + list(range(1, tick_count + 1)))
        
        for command in completed_commands:
            tick_line = [""] * tick_count
            for tick, state in command.history.items():
                if 1 <= tick <= tick_count:
                    tick_line[tick - 1] = state
            
            address_hex = hex(command.address)[2:] if command.address else "unknown"
            instruction_hex = hex(command.instruction)[2:].rjust(8, "0") if command.instruction else "unknown"
            
            writer.writerow([address_hex, instruction_hex, command.id] + tick_line)


def export_to_xlsx(completed_commands: list, tick_count: int, output_path: Path) -> None:    
    workbook = xlsxwriter.Workbook(output_path)
    worksheet = workbook.add_worksheet()

    headers = ['Адрес', 'Код', 'id'] + list(range(1, tick_count + 1))
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, str(header))
    
    for row_num, command in enumerate(completed_commands, 1):
        tick_line = [""] * tick_count
        for tick, state in command.history.items():
            if 1 <= tick <= tick_count:
                tick_line[tick - 1] = state
        
        address_hex = hex(command.address)[2:] if command.address else "unknown"
        instruction_hex = hex(command.instruction)[2:].rjust(8, "0") if command.instruction else "unknown"
        
        row_data = [address_hex, instruction_hex, command.id] + tick_line
        for col_num, value in enumerate(row_data):
            worksheet.write(row_num, col_num, value)
    
    worksheet.set_column(0, 1, 10)
    worksheet.set_column(2, len(headers) - 1, 2.5)
    workbook.close()

