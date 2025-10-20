# trace-riscv-excel-gen
Скрипт для генерации трассы выполнения программы на микропроцессорном ядре Taiga для [ЛР1 Изучение принципов работы микропроцессорного ядра RISC-V](https://gitlab.com/sibragimov/riscv-lab/-/blob/main/main.adoc) 

## Вдохновился
[оригинал](https://github.com/dakone22/riscv-lab-pipeline-generator/tree/master)

У меня лично скрипт выше выдавал пустой результат, поэтому решил его дописать. Если с моим не получится (например, пустой результат в xlsx), попробуйте [его](https://github.com/dakone22/riscv-lab-pipeline-generator/tree/master).

## Использование

### Получение входных данных

1. Запустить симуляцию в среде Modelsim (см. методичку по лабораторной работе)
2. Экспортировать данные симуляции:
   1. Выделить все сигналы (`Ctrl+A`) на Wave-диаграмме и скопировать (`Ctrl+C`) ![copy](img/copy.png)
   2. Активировать окно `List`: вкладка `View` -> `List` и вставить всё туда ![list-tab-activate](img/step1.png)
   3. Открыть это отдельным окном. Выделить все сигналы в этом окне (`Ctrl+A`) и у него выбрать `View` -> `Signal Properties` и проверить, что настройки формата соответствуют картинке (потом закрыть всплывающее окно, не нажимая ОК) ![check-config-format](img/check-config-format.png) 
   6. Экспортировать: `File` -> `Export` -> `Tabular list...` и сохранить в виде файла формата `.lst` (обязательно этот формат!)
      ![export](img/export.png)

### Получение результатов в формате CSV и Excel

- По умолчанию запуск
```
python3 generator.py inputFile.lst [outputFile.csv]
```

- Для генерации сразу в Эксель
```
python3 generator.py inputFile.lst [outputFile.xlsx] --export
```
Может понадобиться установить `pip install xlsxwriter` 
- если нет возможности установить зависимость, в файле `export.py` уберите импорт и у `def export_to_xlsx(..)` замените тело на `pass` -> сможете получить `.csv`
- Если не указать `outputFile`, результат будет сохранен в файле с названием входного файла.
- Есть еще флаг `--verbose` для вывода подробной информации.

### Пример результата
![excel-results](img/excel-results.png)

## При участии

- [@val3rkq](https://github.com/val3rkq)
- [@KalimBaTony](https://github.com/KalimBaTony)
