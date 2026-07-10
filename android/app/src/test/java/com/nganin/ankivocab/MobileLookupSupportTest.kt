package com.nganin.ankivocab

import org.junit.Assert.assertEquals
import org.junit.Test
import org.json.JSONObject

class MobileLookupSupportTest {
    @Test
    fun normalizesProcessTextByTrimmingAndCollapsingWhitespace() {
        val result = MobileLookupSupport.normalizeProcessText("  take\n  off\t soon  ")

        assertEquals("take off soon", result)
    }

    @Test
    fun buildsTelegramResolveUrlWithUsernameWithoutAtAndEncodedText() {
        val result = MobileLookupSupport.telegramResolveUrl("@my_vocab_bot", "take off & go")

        assertEquals("tg://resolve?domain=my_vocab_bot&text=take%20off%20%26%20go", result)
    }

    @Test
    fun buildsTelegramResolveUrlWithRfc3986Encoding() {
        val result = MobileLookupSupport.telegramResolveUrl("my_vocab_bot", "café + *~")

        assertEquals("tg://resolve?domain=my_vocab_bot&text=caf%C3%A9%20%2B%20%2A~", result)
    }

    @Test
    fun buildsMobileLookupUrlFromBackendBaseUrl() {
        val result = MobileLookupSupport.mobileLookupUrl("https://example.test/")

        assertEquals("https://example.test/api/vocab/mobile-lookup", result)
    }

    @Test
    fun buildsMobileLookupBodyWithEscapedText() {
        val result = JSONObject(
            MobileLookupSupport.mobileLookupBody("say \"hi\"\nnow", sendToTelegram = true),
        )

        assertEquals("say \"hi\"\nnow", result.getString("text"))
        assertEquals(true, result.getBoolean("send_to_telegram"))
        assertEquals(2, result.length())
    }

    @Test
    fun formatsMobileLookupResponseForPreviewDialog() {
        val result = MobileLookupSupport.formatMobileLookupResponse(
            """
            {
              "status": "created",
              "message": "Added",
              "preview": {
                "canonical_text": "take off",
                "transcription": "/test/",
                "translation_variants": ["взлетать", "снимать"],
                "explanation": "To leave the ground.",
                "examples": ["The plane took off.", "Take off your shoes."],
                "frequency": 4
              },
              "telegram_sent": true
            }
            """.trimIndent(),
        )

        assertEquals(
            """
            Added

            Word: take off
            Transcription: /test/
            Translation: взлетать, снимать

            To leave the ground.

            The plane took off.
            Take off your shoes.

            Frequency: 4/10

            Sent to Telegram.
            """.trimIndent(),
            result,
        )
    }

    @Test
    fun omitsNullTranscriptionFromPreviewDialog() {
        val result = MobileLookupSupport.formatMobileLookupResponse(
            """
            {
              "message": "Added",
              "preview": {
                "canonical_text": "take off",
                "transcription": null,
                "translation_variants": ["взлетать"],
                "explanation": "To leave the ground.",
                "examples": [],
                "frequency": 4
              },
              "telegram_sent": false
            }
            """.trimIndent(),
        )

        assertEquals(
            """
            Added

            Word: take off
            Translation: взлетать

            To leave the ground.

            Frequency: 4/10
            """.trimIndent(),
            result,
        )
    }
}
