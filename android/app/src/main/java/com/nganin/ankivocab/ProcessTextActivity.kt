package com.nganin.ankivocab

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class ProcessTextActivity : Activity() {
    private val prefs by lazy {
        getSharedPreferences("anki_vocab_settings", Context.MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (intent?.action == Intent.ACTION_PROCESS_TEXT) {
            val selectedText = MobileLookupSupport.normalizeProcessText(
                intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT),
            )
            if (selectedText.isBlank()) {
                showMessage("Vocab", "No selected text was provided.", finishAfter = true)
            } else {
                showLookupDialog(selectedText)
            }
        } else {
            showSettingsDialog(finishAfter = true)
        }
    }

    private fun showLookupDialog(text: String) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(4))
        }
        content.addView(label("Selected text"))
        content.addView(value(text))
        content.addView(actionButton("Preview") { callBackend(text, sendToTelegram = false) })
        content.addView(actionButton("Send directly") { callBackend(text, sendToTelegram = true) })
        content.addView(actionButton("Open Telegram") { openTelegram(text) })
        content.addView(actionButton("Settings") { showSettingsDialog(finishAfter = false) })
        content.addView(actionButton("Close") { finish() })

        AlertDialog.Builder(this)
            .setTitle("Vocab")
            .setView(content)
            .setOnCancelListener { finish() }
            .show()
    }

    private fun showSettingsDialog(finishAfter: Boolean) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(4))
        }
        val backendUrl = input("Backend URL", prefs.getString(KEY_BACKEND_URL, "").orEmpty())
        val mobileToken = input("Mobile token", prefs.getString(KEY_MOBILE_TOKEN, "").orEmpty())
        val botUsername = input("Bot username", prefs.getString(KEY_BOT_USERNAME, "").orEmpty())

        content.addView(label("Backend URL"))
        content.addView(backendUrl)
        content.addView(label("Mobile token"))
        content.addView(mobileToken)
        content.addView(label("Bot username"))
        content.addView(botUsername)

        AlertDialog.Builder(this)
            .setTitle("Vocab settings")
            .setView(content)
            .setPositiveButton("Save") { _, _ ->
                prefs.edit()
                    .putString(KEY_BACKEND_URL, backendUrl.text.toString().trim())
                    .putString(KEY_MOBILE_TOKEN, mobileToken.text.toString().trim())
                    .putString(KEY_BOT_USERNAME, botUsername.text.toString().trim())
                    .apply()
                if (finishAfter) {
                    finish()
                }
            }
            .setNegativeButton("Cancel") { _, _ ->
                if (finishAfter) {
                    finish()
                }
            }
            .setOnCancelListener {
                if (finishAfter) {
                    finish()
                }
            }
            .show()
    }

    private fun openTelegram(text: String) {
        val botUsername = prefs.getString(KEY_BOT_USERNAME, "").orEmpty()
        if (botUsername.isBlank()) {
            showMessage("Missing setting", "Set bot_username first.", finishAfter = false)
            return
        }

        try {
            startActivity(
                Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(MobileLookupSupport.telegramResolveUrl(botUsername, text)),
                ),
            )
            finish()
        } catch (_: ActivityNotFoundException) {
            showMessage("Telegram not found", "Install Telegram or open the bot manually.", false)
        }
    }

    private fun callBackend(text: String, sendToTelegram: Boolean) {
        val backendUrl = prefs.getString(KEY_BACKEND_URL, "").orEmpty()
        val mobileToken = prefs.getString(KEY_MOBILE_TOKEN, "").orEmpty()
        if (backendUrl.isBlank() || mobileToken.isBlank()) {
            showMessage("Missing settings", "Set backend_url and mobile_token first.", false)
            return
        }

        showMessage("Vocab", "Sending request...", finishAfter = false)
        thread {
            val result = runCatching {
                postMobileLookup(backendUrl, mobileToken, text, sendToTelegram)
            }.fold(
                onSuccess = { it },
                onFailure = { "Request failed: ${it.message ?: it::class.java.simpleName}" },
            )
            runOnUiThread {
                showMessage("Vocab", result, finishAfter = false)
            }
        }
    }

    private fun postMobileLookup(
        backendUrl: String,
        mobileToken: String,
        text: String,
        sendToTelegram: Boolean,
    ): String {
        val connection = URL(MobileLookupSupport.mobileLookupUrl(backendUrl))
            .openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.connectTimeout = 15_000
        connection.readTimeout = 60_000
        connection.doOutput = true
        connection.setRequestProperty("Authorization", "Bearer $mobileToken")
        connection.setRequestProperty("Content-Type", "application/json")

        OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use {
            it.write(MobileLookupSupport.mobileLookupBody(text, sendToTelegram))
        }

        val stream = if (connection.responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream
        }
        val response = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (connection.responseCode !in 200..299) {
            return "Backend returned ${connection.responseCode}: $response"
        }
        return MobileLookupSupport.formatMobileLookupResponse(response)
    }

    private fun actionButton(text: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply {
                topMargin = dp(8)
            }
        }
    }

    private fun label(text: String): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = 12f
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply {
                topMargin = dp(8)
            }
        }
    }

    private fun value(text: String): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = 18f
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            )
        }
    }

    private fun input(hint: String, value: String): EditText {
        return EditText(this).apply {
            this.hint = hint
            setText(value)
            setSingleLine(true)
        }
    }

    private fun showMessage(title: String, message: String, finishAfter: Boolean) {
        val scrollView = ScrollView(this).apply {
            setPadding(dp(20), dp(8), dp(20), dp(4))
            addView(value(message))
        }
        AlertDialog.Builder(this)
            .setTitle(title)
            .setView(scrollView)
            .setPositiveButton("OK") { _, _ ->
                if (finishAfter) {
                    finish()
                }
            }
            .setOnCancelListener {
                if (finishAfter) {
                    finish()
                }
            }
            .show()
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    companion object {
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_MOBILE_TOKEN = "mobile_token"
        private const val KEY_BOT_USERNAME = "bot_username"
    }
}
