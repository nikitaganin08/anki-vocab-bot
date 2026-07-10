package com.nganin.ankivocab

import org.json.JSONObject
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

object MobileLookupSupport {
    private val whitespace = Regex("\\s+")

    fun normalizeProcessText(value: CharSequence?): String {
        return value?.toString()?.trim()?.replace(whitespace, " ").orEmpty()
    }

    fun telegramResolveUrl(botUsername: String, text: String): String {
        val username = botUsername.trim().removePrefix("@")
        return "tg://resolve?domain=${encodeQueryParameter(username)}&text=${encodeQueryParameter(text)}"
    }

    fun mobileLookupUrl(backendUrl: String): String {
        return backendUrl.trim().trimEnd('/') + "/api/vocab/mobile-lookup"
    }

    fun mobileLookupBody(text: String, sendToTelegram: Boolean): String {
        return JSONObject()
            .put("text", text)
            .put("send_to_telegram", sendToTelegram)
            .put("return_preview", true)
            .toString()
    }

    fun formatMobileLookupResponse(response: String): String {
        return runCatching {
            val payload = JSONObject(response)
            val message = payload.getString("message")
            val preview = payload.optJSONObject("preview")
            val canonicalText = preview?.getString("canonical_text")

            buildString {
                appendLine(message)
                if (canonicalText != null) {
                    appendLine()
                    appendLine("Word: $canonicalText")
                    val transcription = if (preview.isNull("transcription")) {
                        null
                    } else {
                        preview.getString("transcription")
                    }
                    if (!transcription.isNullOrBlank()) {
                        appendLine("Transcription: $transcription")
                    }
                    appendLine(
                        "Translation: ${
                            preview.stringList("translation_variants").joinToString(", ")
                        }",
                    )
                    appendLine()
                    appendLine(preview.optString("explanation"))
                    val examples = preview.stringList("examples").joinToString("\n")
                    if (examples.isNotBlank()) {
                        appendLine()
                        appendLine(examples)
                    }
                    appendLine()
                    appendLine("Frequency: ${preview.optInt("frequency")}/10")
                }
                if (payload.optBoolean("telegram_sent")) {
                    appendLine()
                    append("Sent to Telegram.")
                }
            }.trim()
        }.getOrElse { response }
    }

    private fun JSONObject.stringList(key: String): List<String> {
        val values = optJSONArray(key) ?: return emptyList()
        return List(values.length()) { index -> values.getString(index) }
    }

    private fun encodeQueryParameter(value: String): String {
        return URLEncoder.encode(value, StandardCharsets.UTF_8.name())
            .replace("+", "%20")
            .replace("*", "%2A")
            .replace("%7E", "~")
    }
}
