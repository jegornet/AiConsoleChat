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

echo Запуск модели с запросом: $PROMPT

temperatures="0.1 0.5 1.0"
token_counts="100 500 1000"

for temp in $temperatures; do
    for tokens in $token_counts; do
        echo `date` Температура $temp, токенов $tokens
        exec_ai $temp $tokens
    done
done

echo `date` Ответы получены, выводы:
./main.py --exec-prompt-file $OUTPUT --model $MODEL --max-tokens 4000
