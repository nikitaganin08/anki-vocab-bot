package com.nganin.ankivocab

import org.junit.Assert.assertEquals
import org.junit.Test

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
    fun buildsMobileLookupUrlFromBackendBaseUrl() {
        val result = MobileLookupSupport.mobileLookupUrl("https://example.test/")

        assertEquals("https://example.test/api/vocab/mobile-lookup", result)
    }

    @Test
    fun buildsMobileLookupBodyWithEscapedTextAndPreviewFlag() {
        val result = MobileLookupSupport.mobileLookupBody("say \"hi\"\nnow", sendToTelegram = true)

        assertEquals(
            "{\"text\":\"say \\\"hi\\\"\\nnow\",\"send_to_telegram\":true,\"return_preview\":true}",
            result,
        )
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
}
