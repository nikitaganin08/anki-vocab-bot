package com.nganin.ankivocab

import java.nio.charset.StandardCharsets

object MobileLookupSupport {
    private val whitespace = Regex("\\s+")

    fun normalizeProcessText(value: CharSequence?): String {
        return value?.toString()?.trim()?.replace(whitespace, " ").orEmpty()
    }

    fun telegramResolveUrl(botUsername: String, text: String): String {
        val username = botUsername.trim().removePrefix("@")
        return "tg://resolve?domain=${percentEncode(username)}&text=${percentEncode(text)}"
    }

    fun mobileLookupUrl(backendUrl: String): String {
        return backendUrl.trim().trimEnd('/') + "/api/vocab/mobile-lookup"
    }

    fun mobileLookupBody(text: String, sendToTelegram: Boolean): String {
        return "{\"text\":\"${jsonEscape(text)}\",\"send_to_telegram\":$sendToTelegram,\"return_preview\":true}"
    }

    fun formatMobileLookupResponse(response: String): String {
        val message = extractString(response, "message") ?: return response
        val canonicalText = extractString(response, "canonical_text")
        return runCatching {
            buildString {
                appendLine(message)
                if (canonicalText != null) {
                    appendLine()
                    appendLine("Word: $canonicalText")
                    val transcription = extractString(response, "transcription")
                    if (!transcription.isNullOrBlank()) {
                        appendLine("Transcription: $transcription")
                    }
                    appendLine(
                        "Translation: ${
                            extractStringArray(response, "translation_variants").joinToString(", ")
                        }",
                    )
                    appendLine()
                    appendLine(extractString(response, "explanation").orEmpty())
                    val examples = extractStringArray(response, "examples").joinToString("\n")
                    if (examples.isNotBlank()) {
                        appendLine()
                        appendLine(examples)
                    }
                    appendLine()
                    appendLine("Frequency: ${extractInt(response, "frequency") ?: 0}/10")
                }
                if (extractBool(response, "telegram_sent")) {
                    appendLine()
                    append("Sent to Telegram.")
                }
            }.trim()
        }.getOrElse { response }
    }

    private fun percentEncode(value: String): String {
        val bytes = value.toByteArray(StandardCharsets.UTF_8)
        return buildString {
            for (byte in bytes) {
                val unsigned = byte.toInt() and 0xff
                if (
                    unsigned in 'A'.code..'Z'.code ||
                    unsigned in 'a'.code..'z'.code ||
                    unsigned in '0'.code..'9'.code ||
                    unsigned.toChar() in "-._~"
                ) {
                    append(unsigned.toChar())
                } else {
                    append('%')
                    append(HEX[unsigned shr 4])
                    append(HEX[unsigned and 0x0f])
                }
            }
        }
    }

    private fun jsonEscape(value: String): String {
        return buildString {
            value.forEach { char ->
                when (char) {
                    '\\' -> append("\\\\")
                    '"' -> append("\\\"")
                    '\n' -> append("\\n")
                    '\r' -> append("\\r")
                    '\t' -> append("\\t")
                    else -> {
                        if (char.code < 0x20) {
                            append("\\u")
                            append(char.code.toString(16).padStart(4, '0'))
                        } else {
                            append(char)
                        }
                    }
                }
            }
        }
    }

    private fun extractString(json: String, key: String): String? {
        val pattern = Regex("\"$key\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"")
        return pattern.find(json)?.groupValues?.get(1)?.let(::jsonUnescape)
    }

    private fun extractStringArray(json: String, key: String): List<String> {
        val arrayPattern = Regex("\"$key\"\\s*:\\s*\\[(.*?)]", RegexOption.DOT_MATCHES_ALL)
        val arrayContent = arrayPattern.find(json)?.groupValues?.get(1) ?: return emptyList()
        val itemPattern = Regex("\"((?:\\\\.|[^\"\\\\])*)\"")
        return itemPattern.findAll(arrayContent)
            .map { jsonUnescape(it.groupValues[1]) }
            .toList()
    }

    private fun extractInt(json: String, key: String): Int? {
        val pattern = Regex("\"$key\"\\s*:\\s*(\\d+)")
        return pattern.find(json)?.groupValues?.get(1)?.toIntOrNull()
    }

    private fun extractBool(json: String, key: String): Boolean {
        val pattern = Regex("\"$key\"\\s*:\\s*(true|false)")
        return pattern.find(json)?.groupValues?.get(1)?.toBooleanStrictOrNull() ?: false
    }

    private fun jsonUnescape(value: String): String {
        return buildString {
            var index = 0
            while (index < value.length) {
                val char = value[index]
                if (char == '\\' && index + 1 < value.length) {
                    when (val next = value[index + 1]) {
                        '\\' -> append('\\')
                        '"' -> append('"')
                        'n' -> append('\n')
                        'r' -> append('\r')
                        't' -> append('\t')
                        else -> append(next)
                    }
                    index += 2
                } else {
                    append(char)
                    index += 1
                }
            }
        }
    }

    private const val HEX = "0123456789ABCDEF"
}
