<template>
    <view class="container">
        <!-- IP input row + TTS config -->
        <view class="ip-row">
            <input class="ip-input" v-model="ip" type="text" placeholder="Device IP" placeholder-style="color: #6B7280" />
            <input class="ip-input port-input" v-model="ttsPort" type="text" placeholder="TTS Port" placeholder-style="color: #6B7280" />
            <button class="btn-load" :class="{ 'btn-tts-connected': ttsConnected }" @click="loadTtsModel" :disabled="ttsLoading">
                <text v-if="ttsLoading">Loading...</text>
                <text v-else-if="!ttsConnected">Load Model</text>
                <text v-else>Connected</text>
            </button>
        </view>

        <!-- Predict server IP + connection test -->
        <view class="ip-row">
            <input class="ip-input" v-model="predictIp" type="text" placeholder="PC IP (Predict)" placeholder-style="color: #6B7280" />
            <button class="btn-predict" :class="{ 'btn-connected': connected }" @click="predictWord" :disabled="predicting">
                <text v-if="!predicting && !connected">Load Model</text>
                <text v-else-if="predicting">Connecting...</text>
                <text v-else-if="connected">Connected</text>
            </button>
        </view>

        <!-- Chat bubbles + action area -->
        <view class="card chat-card">
            <!-- Chat bubble -->
            <scroll-view class="chat-scroll" scroll-y :scroll-into-view="'msg-'+dialogue.length" v-if="dialogue.length">
                <view class="chat-row" v-for="(msg, i) in dialogue" :key="i" :id="'msg-'+i"
                    :class="'chat-row-' + msg.role">
                    <view class="chat-label" v-if="msg.role === 'ai'">Them</view>
                    <view class="chat-bubble" :class="'chat-bubble-' + msg.role">
                        <text class="chat-msg">{{ msg.content }}</text>
                    </view>
                    <view class="chat-label" v-if="msg.role === 'user'">You</view>
                </view>
                <view class="chat-row chat-row-ai" v-if="chatLoading">
                    <view class="chat-label">System</view>
                    <view class="chat-bubble chat-bubble-ai">
                        <text class="chat-loading-text">Generating response...</text>
                    </view>
                </view>
            </scroll-view>

            <!-- Bottom action area -->
            <view class="chat-action" v-if="!dialogue.length && !wordSequence.length && !sentences.length">
                <text class="chat-action-hint">Waiting for data...</text>
            </view>
            <view class="chat-action" v-else>
                <view class="chat-divider" v-if="dialogue.length"></view>
                <!-- Keywords -->
                <view class="chat-tags" v-if="uniqueKeywords.length && !sentences.length">
                    <text class="chat-tag" v-for="(w, i) in uniqueKeywords" :key="i">{{ w.word }}</text>
                </view>
                <!-- Sentence options -->
                <view class="chat-options" v-if="sentences.length">
                    <text class="chat-options-title">Select a sentence to send:</text>
                    <view class="chat-option" v-for="(s, i) in sentences" :key="i"
                        :class="{ 'chat-option-active': selectedIndex === i }"
                        @click="selectSentence(i)">
                        <text class="chat-option-text">{{ s }}</text>
                        <text class="chat-option-check">{{ selectedIndex === i ? '✓' : '' }}</text>
                    </view>
                </view>
            </view>
        </view>

        <!-- Other reply input (voice or keyboard) -->
        <view class="card other-input-card" v-if="dialogue.length">
            <text class="other-input-title">Reply (Voice or Keyboard)</text>
            <view class="other-input-row">
                <input class="other-input" type="text" v-model="otherInput"
                    placeholder="Type reply here..." :disabled="generatingReplies"
                    confirm-type="send" @confirm="sendOtherMessage" />
                <button class="other-send-btn" :disabled="!otherInput.trim() || generatingReplies"
                    @click="sendOtherMessage">
                    <text>{{ generatingReplies ? 'Generating' : 'Send' }}</text>
                </button>
            </view>
        </view>

        <!-- Three-step action buttons -->
        <view class="step-row">
            <button class="step-btn" :class="{ 'step-btn-active': connected }" @click="recognize" :disabled="!connected || recognizing">
                <text>Recognize<text v-if="recognizing">...</text></text>
            </button>
            <button class="step-btn" :class="{ 'step-btn-active': wordSequence.length > 0 }" @click="expandSentence" :disabled="wordSequence.length === 0 || expanding">
                <text>Expand<text v-if="expanding">...</text></text>
            </button>
            <button class="step-btn" :class="{ 'step-btn-active': sentences.length > 0 }" @click="toggleAudio" :disabled="!selectedSentence">
                <text>Audio<text v-if="audioPlaying"> ■</text></text>
            </button>
            <button class="step-btn" :class="{ 'step-btn-active': selectedSentence && !audioHistory.some(h => h.text === selectedSentence) }" @click="saveCurrentAudio" :disabled="!selectedSentence || audioHistory.some(h => h.text === selectedSentence) || isSaving">
                <text>Save<text v-if="isSaving">...</text></text>
            </button>
        </view>

        <!-- Audio history -->
        <view class="card audio-history-card" v-if="audioHistory.length">
            <text class="audio-history-title">Audio History</text>
            <view class="audio-history-item" v-for="(item, i) in audioHistory" :key="i" @click="playFromHistory(item)"
                :class="{ 'audio-history-active': currentAudioPath === item.path && audioPlaying }">
                <text class="audio-history-text">{{ item.text }}</text>
                <text class="audio-history-time">{{ item.time }}</text>
                <text class="audio-history-play-icon">{{ currentAudioPath === item.path && audioPlaying ? '●' : '▶' }}</text>
            </view>
        </view>

        <!-- Prediction results card -->
        <view class="card predict-card" v-if="predictResult">
            <text class="predict-title">Prediction Results</text>
            <text class="predict-file">{{ predictResult.file }}</text>
            <view class="predict-bar-row" v-for="r in predictResult.results" :key="r.class">
                <text class="predict-label">{{ r.class }}</text>
                <view class="predict-bar-bg">
                    <view class="predict-bar-fill" :style="{ width: r.percentage + '%' }"></view>
                </view>
                <text class="predict-pct">{{ r.percentage }}%</text>
                <text class="predict-count">({{ r.count }}/{{ predictResult.total_windows }})</text>
            </view>
        </view>
    </view>
</template>

<script>
    export default {
        data() {
            return {
                ip: '10.0.0.78',
                predictIp: '127.0.0.1',
                predicting: false,
                connected: false,
                predictResult: null,
                ttsPort: '9880',
                ttsLoading: false,
                ttsConnected: false,
                sentences: [],
                wordSequence: [],
                selectedSentence: '',
                selectedIndex: 0,
                audioUrl: '',
                audioPlaying: false,
                audioContext: null,
                downloadTask: null,
                preloadedAudio: {},
                recognizing: false,
                expanding: false,
                audioHistory: [],
                currentAudioPath: '',
                isSaving: false,
                dialogue: [],
                chatLoading: false,
                otherInput: '',
                generatingReplies: false
            }
        },
        computed: {
            uniqueKeywords() {
                const seen = new Set()
                return this.wordSequence.filter(w => {
                    if (w.word === "rest") return false
                    if (seen.has(w.word)) return false
                    seen.add(w.word)
                    return true
                })
            }
        },
        methods: {
            // ─── Audio helpers ───────────────────────────────
            destroyAudioContext() {
                if (this.downloadTask) {
                    this.downloadTask.abort()
                    this.downloadTask = null
                }
                if (this.audioContext) {
                    this.audioContext.destroy()
                    this.audioContext = null
                }
                this.audioPlaying = false
            },
            createAudioContext() {
                this.destroyAudioContext()
                this.audioContext = uni.createInnerAudioContext()
                this.audioContext.onEnded(() => { this.audioPlaying = false })
                this.audioContext.onError((err) => {
                    console.error('InnerAudioContext error:', JSON.stringify(err))
                    uni.showToast({ title: 'Playback failed', icon: 'none' })
                    this.audioPlaying = false
                })
            },
            playAudio(src, text) {
                this.createAudioContext()
                this.currentAudioPath = src
                this.audioContext.src = src
                this.audioContext.play()
                this.audioPlaying = true
            },
            downloadAndPlay(text) {
                const ip = this.predictIp.trim()
                const url = `http://${ip}:5001/api/tts_gen?text=${encodeURIComponent(text)}`
                const self = this

                uni.showLoading({ title: 'Loading audio...' })
                this.downloadTask = uni.downloadFile({
                    url,
                    success: (res) => {
                        uni.hideLoading()
                        self.downloadTask = null
                        // Discard stale response: user already switched sentence
                        if (self.selectedSentence !== text) return
                        if (res.statusCode === 200) {
                            self.preloadedAudio[text] = res.tempFilePath
                            self.playAudio(res.tempFilePath, text)
                            self.sendCurrentToChat()
                        } else {
                            uni.showToast({ title: 'Audio HTTP ' + res.statusCode, icon: 'none' })
                        }
                    },
                    fail: (err) => {
                        uni.hideLoading()
                        self.downloadTask = null
                        console.error('downloadFile error:', JSON.stringify(err))
                        uni.showToast({ title: 'Audio loading failed', icon: 'none' })
                    }
                })
            },
            preloadAllAudio() {
                if (!this.sentences.length) return
                const ip = this.predictIp.trim()
                this.sentences.forEach(text => {
                    if (this.preloadedAudio[text]) return
                    const url = `http://${ip}:5001/api/tts_gen?text=${encodeURIComponent(text)}`
                    uni.downloadFile({
                        url,
                        success: (res) => {
                            if (res.statusCode === 200) {
                                this.preloadedAudio[text] = res.tempFilePath
                            }
                        },
                        fail: (err) => {
                            console.error('Preload failed for:', text, JSON.stringify(err))
                        }
                    })
                })
            },
            // ─── Main methods ────────────────────────────────
            predictWord() {
                if (!this.predictIp.trim()) return
                this.predicting = true
                uni.request({
                    url: `http://${this.predictIp.trim()}:5001/api/ping`,
                    method: 'GET',
                    timeout: 5000,
                    success: (res) => {
                        if (res.statusCode === 200 && res.data && res.data.success) {
                            this.connected = true
                            uni.showToast({ title: 'Connected', icon: 'success' })
                        } else {
                            this.connected = false
                            uni.showToast({ title: 'Connection failed', icon: 'none' })
                        }
                    },
                    fail: () => {
                        this.connected = false
                        uni.showToast({ title: 'Cannot connect to server', icon: 'none' })
                    },
                    complete: () => {
                        this.predicting = false
                    }
                })
            },
            recognize() {
                if (!this.predictIp.trim()) return
                this.recognizing = true
                this.predictResult = null
                this.wordSequence = []
                this.sentences = []
                this.selectedSentence = ''
                this.selectedIndex = 0
                this.preloadedAudio = {}
                this.destroyAudioContext()
                uni.request({
                    url: `http://${this.predictIp.trim()}:5001/api/predict`,
                    method: 'GET',
                    timeout: 60000,
                    success: (res) => {
                        if (res.statusCode === 200 && res.data && res.data.success) {
                            this.predictResult = res.data
                            if (res.data.word_sequence) {
                                this.wordSequence = res.data.word_sequence
                            }
                            uni.showToast({ title: 'Recognition complete', icon: 'success' })
                        } else {
                            const msg = (res.data && res.data.error) || 'Recognition failed'
                            uni.showToast({ title: msg, icon: 'none' })
                        }
                    },
                    fail: () => {
                        uni.showToast({ title: 'Recognition request failed', icon: 'none' })
                    },
                    complete: () => {
                        this.recognizing = false
                    }
                })
            },
            expandSentence() {
                if (!this.wordSequence.length) return
                this.expanding = true
                this.sentences = []
                this.selectedIndex = 0
                this.selectedSentence = ''
                this.preloadedAudio = {}
                this.destroyAudioContext()
                uni.request({
                    url: `http://${this.predictIp.trim()}:5001/api/compose`,
                    method: 'POST',
                    header: { 'Content-Type': 'application/json' },
                    timeout: 60000,
                    data: {
                        word_sequence: this.wordSequence
                    },
                    success: (res) => {
                        if (res.statusCode === 200 && res.data && res.data.success) {
                            if (res.data.sentences && res.data.sentences.length) {
                                this.sentences = res.data.sentences
                                this.selectSentence(0)
                                this.preloadAllAudio()
                            }
                            uni.showToast({ title: 'Expansion complete', icon: 'success' })
                        } else {
                            uni.showToast({ title: 'Expansion failed', icon: 'none' })
                        }
                    },
                    fail: () => {
                        uni.showToast({ title: 'Expansion request failed', icon: 'none' })
                    },
                    complete: () => {
                        this.expanding = false
                    }
                })
            },
            selectSentence(i) {
                this.selectedIndex = i
                this.selectedSentence = this.sentences[i]
                // Destroy old context & abort any in-flight download
                this.destroyAudioContext()
                // Try preloaded cache first
                const preloaded = this.preloadedAudio[this.selectedSentence]
                if (preloaded) {
                    this.playAudio(preloaded, this.selectedSentence)
                    this.sendCurrentToChat()
                    return
                }
                // Try history cache
                const cached = this.audioHistory.find(h => h.text === this.selectedSentence)
                if (cached) {
                    this.playAudio(cached.path, this.selectedSentence)
                    this.sendCurrentToChat()
                    return
                }
                // Fallback: download and play
                this.downloadAndPlay(this.selectedSentence)
            },
            loadTtsModel() {
                if (!this.ttsPort.trim()) return
                this.ttsLoading = true
                uni.request({
                    url: `http://${this.predictIp.trim()}:5001/api/tts_config`,
                    method: 'POST',
                    data: { port: parseInt(this.ttsPort.trim()) },
                    timeout: 10000,
                    success: (res) => {
                        if (res.data && res.data.success) {
                            this.ttsConnected = true
                            uni.showToast({ title: 'TTS model loaded', icon: 'success' })
                        } else {
                            this.ttsConnected = false
                            uni.showToast({ title: 'TTS connection failed', icon: 'none' })
                        }
                    },
                    fail: () => {
                        uni.showToast({ title: 'TTS connection failed', icon: 'none' })
                    },
                    complete: () => {
                        this.ttsLoading = false
                    }
                })
            },
            toggleAudio() {
                if (!this.selectedSentence) return
                // If playing, stop
                if (this.audioPlaying) {
                    this.destroyAudioContext()
                    return
                }
                // Try preloaded cache first
                const preloaded = this.preloadedAudio[this.selectedSentence]
                if (preloaded) {
                    this.playAudio(preloaded, this.selectedSentence)
                    this.sendCurrentToChat()
                    return
                }
                // Try history cache
                const cached = this.audioHistory.find(h => h.text === this.selectedSentence)
                if (cached) {
                    this.playAudio(cached.path, this.selectedSentence)
                    this.sendCurrentToChat()
                    return
                }
                // Fallback: download and play
                this.downloadAndPlay(this.selectedSentence)
            },
            saveCurrentAudio() {
                if (!this.selectedSentence) return
                if (this.audioHistory.find(h => h.text === this.selectedSentence)) {
                    uni.showToast({ title: 'Already saved', icon: 'success' })
                    return
                }

                const ip = this.predictIp.trim()
                const url = `http://${ip}:5001/api/tts_gen?text=${encodeURIComponent(this.selectedSentence)}`
                const text = this.selectedSentence
                const self = this

                this.isSaving = true
                uni.showLoading({ title: 'Saving audio...' })

                // Android native: plus.downloader → copy to public Downloads
                if (typeof plus !== 'undefined' && plus.downloader) {
                    const fileName = `tts_${Date.now()}.wav`
                    const task = plus.downloader.createDownload(url, { filename: `_doc/${fileName}` }, (task, status) => {
                        if (status === 200) {
                            // Copy to public Downloads directory
                            self.copyToPublicDownloads(task.filename, fileName, (publicPath) => {
                                uni.hideLoading()
                                self.isSaving = false
                                self.audioHistory.unshift({ text, path: publicPath, time: new Date().toLocaleString() })
                                uni.showToast({ title: 'Saved to Downloads', icon: 'success' })
                            })
                        } else {
                            uni.hideLoading()
                            self.isSaving = false
                            uni.showToast({ title: 'Save failed', icon: 'none' })
                        }
                    })
                    task.start()
                    return
                }

                // H5 fallback: downloadFile + saveFile
                uni.downloadFile({
                    url,
                    success: (res) => {
                        uni.saveFile({
                            tempFilePath: res.tempFilePath,
                            success: (saveRes) => {
                                uni.hideLoading()
                                self.isSaving = false
                                self.audioHistory.unshift({ text, path: saveRes.savedFilePath, time: new Date().toLocaleString() })
                                uni.showToast({ title: 'Saved successfully', icon: 'success' })
                            },
                            fail: () => {
                                uni.hideLoading()
                                self.isSaving = false
                                uni.showToast({ title: 'Cannot save on desktop', icon: 'none' })
                            }
                        })
                    },
                    fail: () => {
                        uni.hideLoading()
                        self.isSaving = false
                        uni.showToast({ title: 'Download failed', icon: 'none' })
                    }
                })
            },
            copyToPublicDownloads(privatePath, fileName, callback) {
                // Copy from private to public Downloads directory
                if (typeof plus !== 'undefined' && plus.io) {
                    plus.io.requestFileSystem(plus.io.PUBLIC_DOWNLOADS, (fs) => {
                        plus.io.resolveLocalFileSystemURL(privatePath, (srcEntry) => {
                            srcEntry.copyTo(fs.root, fileName, () => {
                                // Read destination file's local URL
                                fs.root.getFile(fileName, { create: false }, (destEntry) => {
                                    callback(destEntry.toLocalURL())
                                }, () => callback(privatePath))
                            }, () => callback(privatePath))
                        }, () => callback(privatePath))
                    }, () => callback(privatePath))
                } else {
                    callback(privatePath)
                }
            },
            sendCurrentToChat() {
                // Add our voice text to chat after playing, wait for other's reply
                const lastMsg = [...this.dialogue].reverse().find(d => d.role === 'user')
                if (lastMsg?.content !== this.selectedSentence) {
                    this.dialogue.push({ role: 'user', content: this.selectedSentence })
                }
            },
            sendOtherMessage() {
                const msg = this.otherInput.trim()
                if (!msg || this.generatingReplies) return
                this.dialogue.push({ role: 'ai', content: msg })
                this.otherInput = ''
                this.generateReplies(msg)
            },
            generateReplies(otherMessage) {
                const history = this.dialogue.slice(0, -1).map(d => ({ role: d.role, content: d.content }))
                this.generatingReplies = true
                this.chatLoading = true
                // Clear old options and selection, wait for 3 new options
                this.sentences = []
                this.selectedIndex = 0
                this.selectedSentence = ''
                this.preloadedAudio = {}
                this.destroyAudioContext()
                uni.request({
                    url: `http://${this.predictIp.trim()}:5001/api/generate_replies`,
                    method: 'POST',
                    header: { 'Content-Type': 'application/json' },
                    timeout: 60000,
                    data: { message: otherMessage, history },
                    success: (res) => {
                        if (res.data && res.data.success && res.data.sentences && res.data.sentences.length) {
                            this.sentences = res.data.sentences
                            this.selectSentence(0)
                            this.preloadAllAudio()
                            uni.showToast({ title: 'Response options ready', icon: 'success' })
                        } else {
                            uni.showToast({ title: 'Failed to generate response', icon: 'none' })
                        }
                    },
                    fail: () => {
                        uni.showToast({ title: 'Response generation failed', icon: 'none' })
                    },
                    complete: () => {
                        this.generatingReplies = false
                        this.chatLoading = false
                    }
                })
            },
            sendToChat(message) {
                const history = this.dialogue.slice(0, -1).map(d => ({ role: d.role, content: d.content }))
                this.chatLoading = true
                uni.request({
                    url: `http://${this.predictIp.trim()}:5001/api/chat`,
                    method: 'POST',
                    header: { 'Content-Type': 'application/json' },
                    timeout: 30000,
                    data: { message, history },
                    success: (res) => {
                        if (res.data && res.data.success && res.data.reply) {
                            this.dialogue.push({ role: 'ai', content: res.data.reply })
                        }
                    },
                    fail: () => {
                        uni.showToast({ title: 'Chat request failed', icon: 'none' })
                    },
                    complete: () => {
                        this.chatLoading = false
                    }
                })
            },
            playFromHistory(item) {
                if (this.audioPlaying && this.currentAudioPath === item.path) {
                    this.destroyAudioContext()
                    return
                }
                this.selectedSentence = item.text
                this.selectedIndex = this.sentences.indexOf(item.text)
                this.playAudio(item.path, item.text)
            },
        }
    }
</script>

<style>
    .container {
        padding: 100rpx 30rpx 40rpx;
        min-height: 100vh;
        background-color: #0A0D21;
    }

    .ip-row {
        display: flex;
        align-items: center;
        gap: 20rpx;
        margin: 20rpx 0;
    }
    .ip-input {
        flex: 1;
        height: 80rpx;
        background-color: #1F2937;
        border-radius: 12rpx;
        padding: 0 30rpx;
        color: #FFFFFF;
        font-size: 32rpx;
    }
    .port-input {
        width: 140rpx;
        flex: none;
    }
    .btn-load {
        height: 80rpx;
        line-height: 80rpx;
        padding: 0 30rpx;
        background-color: #8B5CF6;
        color: #FFFFFF;
        font-weight: bold;
        border-radius: 12rpx;
        font-size: 24rpx;
        white-space: nowrap;
    }
    .btn-load[disabled] {
        opacity: 0.6;
    }
    .btn-tts-connected {
        background-color: #2DD4BF !important;
        color: #000000 !important;
    }

    .card {
        background-color: #1F2937;
        border-radius: 12px;
        padding: 20rpx;
        margin-bottom: 15rpx;
    }

    .chat-card {
        min-height: 400rpx;
        display: flex;
        flex-direction: column;
    }

    /* Other reply input */
    .other-input-card {
        display: flex;
        flex-direction: column;
        gap: 12rpx;
    }
    .other-input-title {
        color: #9CA3AF;
        font-size: 24rpx;
    }
    .other-input-row {
        display: flex;
        gap: 12rpx;
        align-items: center;
    }
    .other-input {
        flex: 1;
        height: 70rpx;
        background-color: #374151;
        color: #F3F4F6;
        border-radius: 10rpx;
        padding: 0 18rpx;
        font-size: 28rpx;
    }
    .other-send-btn {
        width: 140rpx;
        height: 70rpx;
        line-height: 70rpx;
        background-color: #F59E0B;
        color: #000000;
        font-weight: bold;
        border-radius: 10rpx;
        font-size: 28rpx;
        text-align: center;
    }
    .other-send-btn[disabled] {
        opacity: 0.5;
    }
    .image-placeholder {
        padding: 100rpx 0;
        text-align: center;
    }

    /* Predict button */
    .btn-predict {
        height: 90rpx;
        line-height: 90rpx;
        background-color: #F59E0B;
        color: #000000;
        font-weight: bold;
        border-radius: 12rpx;
        font-size: 32rpx;
    }
    .btn-predict[disabled] {
        opacity: 0.5;
    }
    .btn-connected {
        background-color: #2DD4BF !important;
    }

    /* Three-step button row */
    .step-row {
        display: flex;
        gap: 15rpx;
        margin-bottom: 15rpx;
    }
    .step-btn {
        flex: 1;
        height: 80rpx;
        line-height: 80rpx;
        background-color: #374151;
        color: #6B7280;
        border-radius: 12rpx;
        font-size: 28rpx;
        text-align: center;
    }
    .step-btn[disabled] {
        opacity: 0.5;
    }
    .step-btn-active {
        background-color: #2DD4BF;
        color: #000000;
        font-weight: bold;
    }

    /* Prediction results card */
    .predict-card {
        margin-top: 10rpx;
    }
    .predict-title {
        font-size: 30rpx;
        font-weight: bold;
        color: #F59E0B;
        display: block;
        margin-bottom: 10rpx;
    }
    .predict-file {
        font-size: 24rpx;
        color: #6B7280;
        display: block;
        margin-bottom: 20rpx;
    }
    .predict-bar-row {
        display: flex;
        align-items: center;
        gap: 12rpx;
        margin-bottom: 16rpx;
    }
    .predict-label {
        width: 80rpx;
        font-size: 26rpx;
        color: #FFFFFF;
        flex-shrink: 0;
    }
    .predict-bar-bg {
        flex: 1;
        height: 24rpx;
        background-color: #374151;
        border-radius: 12rpx;
        overflow: hidden;
    }
    .predict-bar-fill {
        height: 100%;
        background-color: #2DD4BF;
        border-radius: 12rpx;
        transition: width 0.3s ease;
    }
    .predict-pct {
        width: 70rpx;
        font-size: 24rpx;
        color: #2DD4BF;
        text-align: right;
        flex-shrink: 0;
    }
    .predict-count {
        font-size: 22rpx;
        color: #6B7280;
        flex-shrink: 0;
    }
    /* Chat bubbles */
    .chat-scroll {
        max-height: 600rpx;
        overflow-y: auto;
    }
    .chat-row {
        display: flex;
        align-items: flex-start;
        gap: 12rpx;
        margin-bottom: 20rpx;
        padding: 0 10rpx;
    }
    .chat-row-user {
        justify-content: flex-end;
    }
    .chat-row-ai {
        justify-content: flex-start;
    }
    .chat-label {
        font-size: 22rpx;
        color: #6B7280;
        flex-shrink: 0;
        margin-top: 10rpx;
        width: 40rpx;
        text-align: center;
    }
    .chat-bubble {
        max-width: 75%;
        padding: 16rpx 24rpx;
        border-radius: 16rpx;
        word-break: break-all;
    }
    .chat-bubble-user {
        background-color: #2DD4BF;
        color: #000000;
        border-bottom-right-radius: 4rpx;
    }
    .chat-bubble-ai {
        background-color: #374151;
        color: #FFFFFF;
        border-bottom-left-radius: 4rpx;
    }
    .chat-msg {
        font-size: 30rpx;
        line-height: 1.5;
    }
    .chat-loading-text {
        font-size: 36rpx;
        color: #9CA3AF;
    }

    /* Bottom action area */
    .chat-action {
        padding-top: 10rpx;
    }
    .chat-action-hint {
        color: #6B7280;
        font-size: 32rpx;
        text-align: center;
        display: block;
        padding: 100rpx 0;
    }
    .chat-divider {
        height: 1rpx;
        background-color: #374151;
        margin-bottom: 16rpx;
    }
    .chat-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 12rpx;
        padding: 8rpx 0;
    }
    .chat-tag {
        font-size: 32rpx;
        color: #2DD4BF;
        font-weight: bold;
        background-color: #2DD4BF22;
        padding: 8rpx 20rpx;
        border-radius: 8rpx;
    }
    .chat-options-title {
        font-size: 26rpx;
        color: #9CA3AF;
        display: block;
        margin-bottom: 12rpx;
    }
    .chat-options {
        margin-bottom: 4rpx;
    }
    .chat-option {
        display: flex;
        align-items: center;
        gap: 12rpx;
        padding: 14rpx 20rpx;
        margin-bottom: 10rpx;
        border-radius: 8rpx;
        background-color: #374151;
    }
    .chat-option-active {
        background-color: #2DD4BF22;
        border: 1rpx solid #2DD4BF;
    }
    .chat-option-text {
        flex: 1;
        font-size: 28rpx;
        color: #FFFFFF;
    }
    .chat-option-active .chat-option-text {
        color: #2DD4BF;
        font-weight: bold;
    }
    .chat-option-check {
        font-size: 28rpx;
        color: #2DD4BF;
        flex-shrink: 0;
        width: 36rpx;
        text-align: center;
    }

    /* Audio history */
    .audio-history-card {
        margin-bottom: 15rpx;
    }
    .audio-history-title {
        font-size: 30rpx;
        font-weight: bold;
        color: #2DD4BF;
        display: block;
        margin-bottom: 16rpx;
    }
    .audio-history-item {
        display: flex;
        align-items: center;
        gap: 12rpx;
        padding: 16rpx 20rpx;
        margin-bottom: 8rpx;
        border-radius: 8rpx;
        background-color: #374151;
    }
    .audio-history-active {
        background-color: #2DD4BF22;
        border: 1rpx solid #2DD4BF;
    }
    .audio-history-text {
        flex: 1;
        font-size: 28rpx;
        color: #FFFFFF;
    }
    .audio-history-time {
        font-size: 22rpx;
        color: #6B7280;
        flex-shrink: 0;
    }
    .audio-history-play-icon {
        font-size: 28rpx;
        color: #9CA3AF;
        flex-shrink: 0;
        width: 40rpx;
        text-align: center;
    }
    .audio-history-active .audio-history-play-icon {
        color: #2DD4BF;
    }
    .audio-history-active .audio-history-text {
        color: #2DD4BF;
        font-weight: bold;
    }
</style>
