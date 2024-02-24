# Транслятор и модель

- P33081, Кочнев Роман Дмитриевич.
- `asm | acc | neum | hw | instr | binary | trap| mem | pstr | prob2 | spi`
- Без усложнения

## Changelog
- В логи выводится, находимся ли мы в прерывании или нет
- Из логов удалено название метода, из которого выводятся логи, т.к. почти все логи из одного метода
- Добавлен провод DR -> CR для ускорения Inst fetch
- Обработка вложенных прерываний
- Описана возможность запускать отдельные модули с консоли

## Язык программирования

### Синтаксис

    **Форма Бэкуса-Наура:**

```ebnf
<программа> ::= <строка_программы> | <строка_программы> <программа>
<строка_программы> ::= <адрес> | [<метка>] <адресная команда> <операнд> | 
[<метка>] <безадресная команда> | [<метка>] <метка константы> <константа> | <пустая строка> 

<метка> ::= <слово>
<адресная команда> = add | load | store | ... | sub | jmp | (см. систему команд)
<безадресная команда> ::= cla | di | ei | ... | hlt
<операнд> ::= <число> | <метка>
<константа> ::= <число> | <число> '<слово>'
<слово> ::= <символ> | <слово> <символ>
<число> ::= <цифра> | <число> <цифра>
<цифра> ::= 0| 1 | 2 | .. | 8 | 9
<символ> ::= a | b | c | ... | z | A | B | C | ... | Z | <цифра>
```

**Пояснение:**

Каждая непустая строка программы это одно из нижеперечисленных:

* **адресная команда**
    * может иметь метку в начале
    * указывается название команды и адрес операнда через пробел
* **безадресная команда**
    * может иметь метку в начале
    * указывается только название команды
* **константа**
    * может иметь метку в начале
    * указывается метка константы `word:` и константа
    * константа может быть 16-битным знаковым числом
    * константа может быть строкой: указывается длина строки и строка через пробел
* **адрес**
    * указывается специальное слово `org` и адрес в десятичном формате

Пример программы, вычисляющей С = A + B

```asm
org 5
A: word: 10
B: word: 15
C: word: 0

start: cla
load A
add B
store C
hlt
```

**Семантика**

- Видимость данных -- глобальная
- Поддерживаются целочисленные литералы, находящиеся в диапазоне от $`-2^{31}`$ до $`2^{31}-1`$
- Поддерживаются строковые литералы, символы стоки необходимо заключить в кавычки, перед строкой через запятую необходимо указать длину
- Код выполняется последовательно

- Программа обязательно должна включать метку `start:`, указывающую на 1-ю выполняемую интсрукцию. Эта метка не может
  указывать на константу.
- Название метки не должно совпадать с названием команды и не может начинаться с цифры.
- Метки находятся на одной строке с командами, операнды находятся на одной строке с командами.
- Пустые строки игнорируются, количество пробелов в начале и конце строки не важно.
- Любой текст, расположенный в конце строки после символа `';'` трактуется как комментарий.

Память выделяется статически, при запуске модели.

## Организация памяти

* Память команд и данныx --- общая
* Размер машинного слова --- `32` бит
* Память содержит `2^11` ячеек
* Адрес `2045` является указателем стека при старте процессора. Стек растет вверх.
* Ячейка с адресом `2046` маппится на устройство ввода
* Ячейка с адресом `2047` маппится на устройство вывода


* Поддерживаются следующие **виды адресаций**:
    * **Прямая**: в качестве аргумента команды передается адрес ячейки, значение в которой будет использовано как
      операнд.
      Например, если `mem[30] = 25`, то команда `add 30` обозначает, что к значению в аккумуляторе добавится число 25.

    * **Косвенная**: в качестве аргумента команды передается адрес, по которому лежит адрес операнда.
      Например, если `mem[30] = 25`, `mem[33] = 30`, то команда `add (33)` также обозначает, что к аккумулятору
      добавится значение 25.


* Существует несколько **регистров**:
    * Аккумулятор (AC): в него записываются результаты всех операций
    * Счетчик команд (IP): хранит адрес следующей выполняемой команды
    * Указатель стека (SP): при вызове прерывания текущее состояние счетчика команд сохраняется на стеке
    * Регистр состояния (PS): хранит маркер того, что наступило прерывание

      ```
        | ie/id | ir | N | Z | C |
         4        3    2   1   0
      ```
        * 0-й бит хранит значение флага C
        * 1-й бит хранит значение флага Z
        * 2-й бит хранит значение флага N
        * 3-й бит содержит 1, если поступил запрос прерывания, и 0 иначе
        * 4-й бит содержит 1, если прерывания разрешены (interrupts enabled) и 0, если запрещены (interrupts disabled)


* Регистр данных (DR): хранит данные для записи в память и считывания из памяти
* Регистр адреса (AR): хранит адрес последней ячейки в памяти, к которой было обращение

## Система команд

Особенности процессора:

- Машинное слово -- `32` бита, знаковое.
- В качестве аргументов команды принимают `11` битные беззнаковые адреса
- 
## Первые 4 бита - позволяют задать тип аргумента
- 1 - Показывает длину текстовой переменной
- 2 - Ссылка на адрес
- 3 - Целочисленная переменная 

Каждая команда выполняется в несколько циклов:

1. Цикл выборки команды: по адресу из счетчика команд из памяти достается команда

- `IP -> AR, IP + 1 -> IP, mem[AR] -> DR, DR -> CR`

2. Цикл выборки операнда (для адресных команд): в регистр данных помещается адрес операнда, регистр данных передавется в
   регистр адреса, из памяти в регистр данных записывается значение операнда

- `CR[addr] -> DR, DR -> AR, mem[AR] -> DR`

3. Цикл исполнения: совершаются действия, необходимые для выполнения команды. Результаты вычисления записываются в
   аккумулятор
4. Цикл прерывания: проверяется, не произошел ли запрос на прерывание

### Набор инструкций

| Язык  | Адресная | Ветвление | Количество тактов<br/>(без выборки адреса) | Описание                                                                |
|:------|:---------|-----------|:-------------------------------------------|:------------------------------------------------------------------------|
| load  | +        | -         | 3                                          | загрузить значение из заданной ячейки                                   |
| store | +        | -         | 3                                          | загрузить значение в заданную ячейку                                    |
| add   | +        | -         | 3                                          | добавить значение из заданной ячейки к аккумулятору                     |
| sub   | +        | -         | 3                                          | вычесть значение из заданной ячейки из аккумулятора                     |
| jmp   | +        | +         | 3                                          | перейти в заданную ячейку                                               |
| cmp   | +        | -         | 3                                          | выставить флаги как результат вычитания заданной ячейки из аккумулятора |
| jmn   | +        | +         | 3                                          | переход, если N == 1                                                    |
| jmnn  | +        | +         | 3                                          | переход, если N == 0                                                    |
| jmc   | +        | +         | 3                                          | переход,  если C == 1                                                   |
| jmnc  | +        | +         | 3                                          | переход, если C == 0                                                    |
| jmz   | +        | +         | 3                                          | переход, если Z == 1                                                    |
| jmnz  | +        | +         | 3                                          | переход, если Z == 0                                                    |
| asl   | -        | -         | 2                                          | сдвинуть значение в аккумуляторе влево                                  |
| asr   | -        | -         | 2                                          | сдвинуть значение в аккумуляторе вправо                                 |
| dec   | -        | -         | 2                                          | уменьшить значение в аккумуляторе на 1                                  |
| inc   | -        | -         | 2                                          | увеличить значение в аккумуляторе на 1                                  |
| cla   | -        | -         | 2                                          | очистить аккумулятор                                                    |
| hlt   | -        | -         | 2                                          | остановить работу программы                                             |
| iret  | -        | -         | 2                                          | возрат из прерывания                                                    |
| push  | -        | -         | 2                                          | положить значение из аккумулятора на стек                               |
| pop   | -        | -         | 2                                          | достать значение с вершины стека и записать в аккумулятор               |
| di    | -        | -         | 2                                          | запретить прерывания                                                    |
| ei    | -        | -         | 2                                          | разрешить прерывания                                                    |
| nop   | -        | -         | 1                                          | отсутствие операции                                                     |


### Кодирование инструкций

- Машинный код сереализуется в бинарный файл

Пример сереализованной команды `load A000` и константы 20:

A0000014



## Транслятор

Интерфейс командной строки: `translator.py <input_file> <target_file>`

Реализовано в модуле: [translator](./translator.py)

Этапы трансляции (функция `translate`):

1. Выделение меток из кода, проверка их корректности (не совпадают с названиями команд, отсуствуют дубликаты)
2. Парсинг кода построчно, определение типа команды (адресная, безадресная, константа)
3. Генерация машинного кода в зависимости от типа команды

Правила генерации машинного кода:

- Метки не сохраняются в машинном коде. Метки, использованные в качестве операнда, преобразуются к адресам команд

## Модель процессора

Интерфейс командной строки: `machine.py <machine_code_file> <input_file>`

Реализовано в модуле: [machine](./machine.py).

### DataPath

Реализован в классе `DataPath`.



`data_memory` -- однопортовая память, поэтому либо читаем, либо пишем.
`registers`
Сигналы (реализованы в виде методов класса):
В

- `set_reg` -- защёлкнуть выбранное значение в регистре с указанным именем
- `rd` --- считать данные из `mem[AR]` в регистр `DR`
- `wr` --- записать данные из регистра `DR` в `mem[AR]`

В виде отдельного класса реализовано арифметико-логическое устройство (АЛУ)

- в данном классе реализован метод `calc`, принимающий аргументы с одного или двух входов и совершающий над ними
  арифметико-логическую операцию
- в результате выполнения операций устанавливаются следующие флаги
    - `Z` -- значение в аккумуляторе равно 0
    - `N` -- значение в аккумуляторе отрицательно
    - `C` -- произошло переполнение (перенос из 16-го бита)

### ControlUnit

Реализован в классе `ControlUnit`.


- Метод `decode_and_execute_instruction` моделирует выполнение полного цикла инструкции (цикл выборки инструкции,
  операнда, исполнения)
- После завершения цикла исполнения проверяется, не произошел ли запрос прерывания, и разрешены ли прерывания. Если оба
  условия верны, то вызывается метод `process_interrupt`
- В рамках реализованной модели на python существуют счетчик количества инструкций только для наложения ограничения на
  кол-во шагов моделирования

Особенности работы модели:

- Цикл симуляции осуществляется в функции `simulation`.
- Шаг моделирования соответствует одному такту процессора с выводом состояния в журнал.
- Для журнала состояний процессора используется стандартный модуль `logging`.
- Количество инструкций для моделирования лимитировано.
- Остановка моделирования осуществляется при:
    - превышении лимита количества выполняемых инструкций;
    - исключении `Incorrect unary operation` или `Incorrect binary operation`-- если в ALU поданны некорректные бинврные или унарные операции
    - если выполнена инструкция `hlt`.

- обработка прерываний осуществляется в методе `process_interrupt`
    - на стек сохраняются текущие значения счетчика команд (IP), и регистра состояния (PS)
    - в IP записывается адрес из вектора прерываний (хранится в ячейке 0)
    - выполняются все команды для обработки прерывания. При выполнении команды  `iret` происходит возврат в основную
      программу
    - из стека достаются значения IP и PS и присваиваются соответствующим регистрам

Проверка наличия запроса прерывания осуществляется после завершения цикла выполнения очередной команды.

- Вложенные прерывания возможны, программист должен управлять запретом и разрешением прерываний самостоятельно при
  помощи команд:
    - ei (enable interrupt) --- разрешить прерывания
    - di (disable interrupt) --- запретить прерывания
- Все регистры кроме PS и IP программист должен самостоятельно сохранять на стек в методе-обработчике прерываний.

## Тестирование

Реализованные програмы

1. [hello world](test/hi.test): вывести на экран строку `'Hello World!'`
2. [cat](test/cat.test): программа `cat`, повторяем ввод на выводе.
3. [hello_username](test/hellouser.test) -- программа `hello_username`: запросить у пользователя его
   имя, считать его, вывести на экран приветствие
4. [prob2](test/prob2.test): найти сумму всех четных чисел Фибоначчи, не превышающих `4 000 000`.

Интеграционные тесты реализованы тут [integration_test](./integration_test.py):

- через golden tests, конфигурация которых лежит в папке [golden](./golden)



```

Выводится листинг всех регистров после каждой команды.

- Значения всех регистров, кроме PS и CR выводятся в десятичном формате
- Значение регистра `PS` выводится в двоичном формате
- В качестве значения регистра `CR`выводятся код оператора и операнд (при наличии)
- Если в какой-то регистр записан символ, в листинге выводится его код

Также в лог выводятся события вида `INPUT symbol` и `OUTPUT symbol`

``` shell

(poma12390-py3.12) PS C:\Users\pomat\Documents\3course\АК\csa-rolling> python machine.py ./output.bin ./input/hello.txt
INPUT h


Command: load | AC 12      | IP: 26   | AR: 2    | PS: 01000 | DR: 12      | SP : 2045 | mem[AR] 12      | mem[SP] : 0   | CR: load 2       |


Command: store | AC 12      | IP: 27   | AR: 16   | PS: 01000 | DR: 12      | SP : 2045 | mem[AR] 12      | mem[SP] : 0   | CR: store 16     |


Command: load | AC 2       | IP: 28   | AR: 15   | PS: 01000 | DR: 2       | SP : 2045 | mem[AR] 2       | mem[SP] : 0   | CR: load 15      |
INPUT e


Command: inc  | AC 3       | IP: 29   | AR: 28   | PS: 01000 | DR: 2       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 3       | IP: 30   | AR: 15   | PS: 01000 | DR: 3       | SP : 2045 | mem[AR] 3       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 72      | IP: 31   | AR: 3    | PS: 01000 | DR: 72      | SP : 2045 | mem[AR] 72      | mem[SP] : 0   | CR: load 15      |
INPUT l
OUTPUT H


Command: store | AC 72      | IP: 32   | AR: 2047 | PS: 01000 | DR: 72      | SP : 2045 | mem[AR] 72      | mem[SP] : 0   | CR: store 17     |
INPUT l


Command: load | AC 12      | IP: 33   | AR: 16   | PS: 01000 | DR: 12      | SP : 2045 | mem[AR] 12      | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 11      | IP: 34   | AR: 33   | PS: 01001 | DR: 12      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 11      | IP: 35   | AR: 16   | PS: 01001 | DR: 11      | SP : 2045 | mem[AR] 11      | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 11      | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 11      | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 3       | IP: 28   | AR: 15   | PS: 01000 | DR: 3       | SP : 2045 | mem[AR] 3       | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 4       | IP: 29   | AR: 28   | PS: 01000 | DR: 3       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 4       | IP: 30   | AR: 15   | PS: 01000 | DR: 4       | SP : 2045 | mem[AR] 4       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 101     | IP: 31   | AR: 4    | PS: 01000 | DR: 101     | SP : 2045 | mem[AR] 101     | mem[SP] : 0   | CR: load 15      |
OUTPUT e


Command: store | AC 101     | IP: 32   | AR: 2047 | PS: 01000 | DR: 101     | SP : 2045 | mem[AR] 101     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 11      | IP: 33   | AR: 16   | PS: 01000 | DR: 11      | SP : 2045 | mem[AR] 11      | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 10      | IP: 34   | AR: 33   | PS: 01001 | DR: 11      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 10      | IP: 35   | AR: 16   | PS: 01001 | DR: 10      | SP : 2045 | mem[AR] 10      | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 10      | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 10      | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 4       | IP: 28   | AR: 15   | PS: 01000 | DR: 4       | SP : 2045 | mem[AR] 4       | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 5       | IP: 29   | AR: 28   | PS: 01000 | DR: 4       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 5       | IP: 30   | AR: 15   | PS: 01000 | DR: 5       | SP : 2045 | mem[AR] 5       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 108     | IP: 31   | AR: 5    | PS: 01000 | DR: 108     | SP : 2045 | mem[AR] 108     | mem[SP] : 0   | CR: load 15      |
OUTPUT l


Command: store | AC 108     | IP: 32   | AR: 2047 | PS: 01000 | DR: 108     | SP : 2045 | mem[AR] 108     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 10      | IP: 33   | AR: 16   | PS: 01000 | DR: 10      | SP : 2045 | mem[AR] 10      | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 9       | IP: 34   | AR: 33   | PS: 01001 | DR: 10      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 9       | IP: 35   | AR: 16   | PS: 01001 | DR: 9       | SP : 2045 | mem[AR] 9       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 9       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 9       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 5       | IP: 28   | AR: 15   | PS: 01000 | DR: 5       | SP : 2045 | mem[AR] 5       | mem[SP] : 0   | CR: load 15      |
INPUT o


Command: inc  | AC 6       | IP: 29   | AR: 28   | PS: 01000 | DR: 5       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 6       | IP: 30   | AR: 15   | PS: 01000 | DR: 6       | SP : 2045 | mem[AR] 6       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 108     | IP: 31   | AR: 6    | PS: 01000 | DR: 108     | SP : 2045 | mem[AR] 108     | mem[SP] : 0   | CR: load 15      |
OUTPUT l


Command: store | AC 108     | IP: 32   | AR: 2047 | PS: 01000 | DR: 108     | SP : 2045 | mem[AR] 108     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 9       | IP: 33   | AR: 16   | PS: 01000 | DR: 9       | SP : 2045 | mem[AR] 9       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 8       | IP: 34   | AR: 33   | PS: 01001 | DR: 9       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          | 


Command: store | AC 8       | IP: 35   | AR: 16   | PS: 01001 | DR: 8       | SP : 2045 | mem[AR] 8       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 8       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 8       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 6       | IP: 28   | AR: 15   | PS: 01000 | DR: 6       | SP : 2045 | mem[AR] 6       | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 7       | IP: 29   | AR: 28   | PS: 01000 | DR: 6       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 7       | IP: 30   | AR: 15   | PS: 01000 | DR: 7       | SP : 2045 | mem[AR] 7       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 111     | IP: 31   | AR: 7    | PS: 01000 | DR: 111     | SP : 2045 | mem[AR] 111     | mem[SP] : 0   | CR: load 15      |
OUTPUT o


Command: store | AC 111     | IP: 32   | AR: 2047 | PS: 01000 | DR: 111     | SP : 2045 | mem[AR] 111     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 8       | IP: 33   | AR: 16   | PS: 01000 | DR: 8       | SP : 2045 | mem[AR] 8       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 7       | IP: 34   | AR: 33   | PS: 01001 | DR: 8       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 7       | IP: 35   | AR: 16   | PS: 01001 | DR: 7       | SP : 2045 | mem[AR] 7       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 7       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 7       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 7       | IP: 28   | AR: 15   | PS: 01000 | DR: 7       | SP : 2045 | mem[AR] 7       | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 8       | IP: 29   | AR: 28   | PS: 01000 | DR: 7       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 8       | IP: 30   | AR: 15   | PS: 01000 | DR: 8       | SP : 2045 | mem[AR] 8       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 32      | IP: 31   | AR: 8    | PS: 01000 | DR: 32      | SP : 2045 | mem[AR] 32      | mem[SP] : 0   | CR: load 15      |
OUTPUT


Command: store | AC 32      | IP: 32   | AR: 2047 | PS: 01000 | DR: 32      | SP : 2045 | mem[AR] 32      | mem[SP] : 0   | CR: store 17     |


Command: load | AC 7       | IP: 33   | AR: 16   | PS: 01000 | DR: 7       | SP : 2045 | mem[AR] 7       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 6       | IP: 34   | AR: 33   | PS: 01001 | DR: 7       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 6       | IP: 35   | AR: 16   | PS: 01001 | DR: 6       | SP : 2045 | mem[AR] 6       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 6       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 6       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 8       | IP: 28   | AR: 15   | PS: 01000 | DR: 8       | SP : 2045 | mem[AR] 8       | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 9       | IP: 29   | AR: 28   | PS: 01000 | DR: 8       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 9       | IP: 30   | AR: 15   | PS: 01000 | DR: 9       | SP : 2045 | mem[AR] 9       | mem[SP] : 0   | CR: store 15     |


Command: load | AC 119     | IP: 31   | AR: 9    | PS: 01000 | DR: 119     | SP : 2045 | mem[AR] 119     | mem[SP] : 0   | CR: load 15      |
OUTPUT w


Command: store | AC 119     | IP: 32   | AR: 2047 | PS: 01000 | DR: 119     | SP : 2045 | mem[AR] 119     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 6       | IP: 33   | AR: 16   | PS: 01000 | DR: 6       | SP : 2045 | mem[AR] 6       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 5       | IP: 34   | AR: 33   | PS: 01001 | DR: 6       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 5       | IP: 35   | AR: 16   | PS: 01001 | DR: 5       | SP : 2045 | mem[AR] 5       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 5       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 5       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 9       | IP: 28   | AR: 15   | PS: 01000 | DR: 9       | SP : 2045 | mem[AR] 9       | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 10      | IP: 29   | AR: 28   | PS: 01000 | DR: 9       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 10      | IP: 30   | AR: 15   | PS: 01000 | DR: 10      | SP : 2045 | mem[AR] 10      | mem[SP] : 0   | CR: store 15     |


Command: load | AC 111     | IP: 31   | AR: 10   | PS: 01000 | DR: 111     | SP : 2045 | mem[AR] 111     | mem[SP] : 0   | CR: load 15      |
OUTPUT o


Command: store | AC 111     | IP: 32   | AR: 2047 | PS: 01000 | DR: 111     | SP : 2045 | mem[AR] 111     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 5       | IP: 33   | AR: 16   | PS: 01000 | DR: 5       | SP : 2045 | mem[AR] 5       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 4       | IP: 34   | AR: 33   | PS: 01001 | DR: 5       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 4       | IP: 35   | AR: 16   | PS: 01001 | DR: 4       | SP : 2045 | mem[AR] 4       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 4       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 4       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 10      | IP: 28   | AR: 15   | PS: 01000 | DR: 10      | SP : 2045 | mem[AR] 10      | mem[SP] : 0   | CR: load 15      | 


Command: inc  | AC 11      | IP: 29   | AR: 28   | PS: 01000 | DR: 10      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 11      | IP: 30   | AR: 15   | PS: 01000 | DR: 11      | SP : 2045 | mem[AR] 11      | mem[SP] : 0   | CR: store 15     |


Command: load | AC 114     | IP: 31   | AR: 11   | PS: 01000 | DR: 114     | SP : 2045 | mem[AR] 114     | mem[SP] : 0   | CR: load 15      |
OUTPUT r


Command: store | AC 114     | IP: 32   | AR: 2047 | PS: 01000 | DR: 114     | SP : 2045 | mem[AR] 114     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 4       | IP: 33   | AR: 16   | PS: 01000 | DR: 4       | SP : 2045 | mem[AR] 4       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 3       | IP: 34   | AR: 33   | PS: 01001 | DR: 4       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 3       | IP: 35   | AR: 16   | PS: 01001 | DR: 3       | SP : 2045 | mem[AR] 3       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 3       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 3       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 11      | IP: 28   | AR: 15   | PS: 01000 | DR: 11      | SP : 2045 | mem[AR] 11      | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 12      | IP: 29   | AR: 28   | PS: 01000 | DR: 11      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 12      | IP: 30   | AR: 15   | PS: 01000 | DR: 12      | SP : 2045 | mem[AR] 12      | mem[SP] : 0   | CR: store 15     |


Command: load | AC 108     | IP: 31   | AR: 12   | PS: 01000 | DR: 108     | SP : 2045 | mem[AR] 108     | mem[SP] : 0   | CR: load 15      |
OUTPUT l


Command: store | AC 108     | IP: 32   | AR: 2047 | PS: 01000 | DR: 108     | SP : 2045 | mem[AR] 108     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 3       | IP: 33   | AR: 16   | PS: 01000 | DR: 3       | SP : 2045 | mem[AR] 3       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 2       | IP: 34   | AR: 33   | PS: 01001 | DR: 3       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 2       | IP: 35   | AR: 16   | PS: 01001 | DR: 2       | SP : 2045 | mem[AR] 2       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 2       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 2       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 12      | IP: 28   | AR: 15   | PS: 01000 | DR: 12      | SP : 2045 | mem[AR] 12      | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 13      | IP: 29   | AR: 28   | PS: 01000 | DR: 12      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 13      | IP: 30   | AR: 15   | PS: 01000 | DR: 13      | SP : 2045 | mem[AR] 13      | mem[SP] : 0   | CR: store 15     |


Command: load | AC 100     | IP: 31   | AR: 13   | PS: 01000 | DR: 100     | SP : 2045 | mem[AR] 100     | mem[SP] : 0   | CR: load 15      |
OUTPUT d


Command: store | AC 100     | IP: 32   | AR: 2047 | PS: 01000 | DR: 100     | SP : 2045 | mem[AR] 100     | mem[SP] : 0   | CR: store 17     |


Command: load | AC 2       | IP: 33   | AR: 16   | PS: 01000 | DR: 2       | SP : 2045 | mem[AR] 2       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 1       | IP: 34   | AR: 33   | PS: 01001 | DR: 2       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 1       | IP: 35   | AR: 16   | PS: 01001 | DR: 1       | SP : 2045 | mem[AR] 1       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 1       | IP: 36   | AR: 37   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |


Command: jmp  | AC 1       | IP: 27   | AR: 27   | PS: 01001 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmp 27       |


Command: load | AC 13      | IP: 28   | AR: 15   | PS: 01000 | DR: 13      | SP : 2045 | mem[AR] 13      | mem[SP] : 0   | CR: load 15      |


Command: inc  | AC 14      | IP: 29   | AR: 28   | PS: 01000 | DR: 13      | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: inc          |


Command: store | AC 14      | IP: 30   | AR: 15   | PS: 01000 | DR: 14      | SP : 2045 | mem[AR] 14      | mem[SP] : 0   | CR: store 15     |


Command: load | AC 33      | IP: 31   | AR: 14   | PS: 01000 | DR: 33      | SP : 2045 | mem[AR] 33      | mem[SP] : 0   | CR: load 15      |
OUTPUT !


Command: store | AC 33      | IP: 32   | AR: 2047 | PS: 01000 | DR: 33      | SP : 2045 | mem[AR] 33      | mem[SP] : 0   | CR: store 17     |


Command: load | AC 1       | IP: 33   | AR: 16   | PS: 01000 | DR: 1       | SP : 2045 | mem[AR] 1       | mem[SP] : 0   | CR: load 16      |


Command: dec  | AC 0       | IP: 34   | AR: 33   | PS: 01011 | DR: 1       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: dec          |


Command: store | AC 0       | IP: 35   | AR: 16   | PS: 01011 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: store 16     |


Command: jmz  | AC 0       | IP: 37   | AR: 37   | PS: 01011 | DR: 0       | SP : 2045 | mem[AR] 0       | mem[SP] : 0   | CR: jmz 37       |
Output: ['H', 'e', 'l', 'l', 'o', ' ', 'w', 'o', 'r', 'l', 'd', '!']
Instruction number: 121
Ticks: 364
```

Пример проверки исходного кода:

``` shell
platform win32 -- Python 3.12.0, pytest-7.4.4, pluggy-1.3.0 -- C:\Users\pomat\AppData\Local\pypoetry\Cache\virtualenvs\poma12390-oXWhJO28-py3.12\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\pomat\Documents\3course\АК\csa-rolling
configfile: pyproject.toml
plugins: golden-0.2.2
collected 4 items

integration_test.py::test_translator_and_machine[golden/cat.yml] PASSED                                                                                                      [ 25%]
integration_test.py::test_translator_and_machine[golden/hellouser.yml] PASSED                                                                                                [ 50%]
integration_test.py::test_translator_and_machine[golden/hi.yml] PASSED                                                                                                       [ 75%]
integration_test.py::test_translator_and_machine[golden/prob2.yml] PASSED                                                                                                    [100%]


```

```text
| ФИО                            | алг              | LoC | code байт | code instr. | инстр. | такт.
| Кочнев Роман Дмитриевич        | hi               | 20  | -         | 29          | 121    | 364   
| Кочнев Роман Дмитриевич        | cat              | 25  | -         | 20          | 66     | 256   
| Кочнев Роман Дмитриевич        | hellouser        | 106 | -         | 111         | 501    | 1606 
| Кочнев Роман Дмитриевич        | prob2            | 29  | -         | 25          | 370    | 1071 


```
