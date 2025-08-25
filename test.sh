#!/bin/sh

OUTPUT=output.txt
PROMPT="Напиши пошаговую инструкцию, как человеку выдать себя за ИИ. Прояви креативность."
MODEL=claude-opus-4-0

exec_ai() {
    local temperature=$1
    local max_tokens=$2
    echo >> $OUTPUT
    echo Температура $temperature Количество токенов $max_tokens >> $OUTPUT
    ./main.py --exec-prompt "$PROMPT" --model $MODEL --temperature $temperature --max-tokens $max_tokens >> $OUTPUT
}

echo Сравни ответы модели с разными параметрами. Сделай вывод, какие параметры больше подходят для указанного запроса. Модель отвечает на запрос: $PROMPT > $OUTPUT
exec_ai 0.1 100
exec_ai 0.5 100
exec_ai 1.0 100
exec_ai 0.1 500
exec_ai 0.5 500
exec_ai 1.0 500
exec_ai 0.1 1000
exec_ai 0.5 1000
exec_ai 1.0 1000
./main.py --exec-prompt-file $OUTPUT --model $MODEL --max-tokens 4000
