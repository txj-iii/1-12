<template>
    <view class="container">
        <view class="nav-bar">
            <view class="nav-back" @click="goBack">
                <text class="back-arrow">&#x2190;</text>
                <text class="back-text">Back</text>
            </view>
            <text class="nav-title">Analysis Report</text>
            <view style="width: 120rpx;"></view>
        </view>

        <view class="card summary-card">
            <view class="summary-row">
                <text class="summary-label">Diagnosis</text>
                <text class="summary-value">{{ diagnosis }}</text>
            </view>
            <view class="summary-row">
                <text class="summary-label">Accuracy</text>
                <text class="summary-value">{{ accuracy }}%</text>
            </view>
            <view class="summary-row">
                <text class="summary-label">Mode</text>
                <text class="summary-value">{{ mode }}</text>
            </view>
        </view>

        <view class="card report-card">
            <text class="report-title">AI Analysis Report</text>
            <scroll-view scroll-y class="report-scroll">
                <text class="report-text">{{ report }}</text>
            </scroll-view>
        </view>
    </view>
</template>

<script>
    export default {
        data() {
            return {
                diagnosis: '--',
                accuracy: '--',
                mode: '--',
                report: 'Loading...'
            }
        },
        onLoad(options) {
            if (options.diagnosis) this.diagnosis = decodeURIComponent(options.diagnosis)
            if (options.accuracy) this.accuracy = options.accuracy
            if (options.mode) this.mode = options.mode
            if (options.report) this.report = decodeURIComponent(options.report)
        },
        methods: {
            goBack() {
                uni.navigateBack()
            }
        }
    }
</script>

<style>
    .container {
        padding: 100rpx 30rpx 40rpx;
        min-height: 100vh;
        background-color: #0A0D21;
    }

    .nav-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 100rpx;
        margin-bottom: 20rpx;
    }
    .nav-back {
        display: flex;
        align-items: center;
        gap: 10rpx;
        padding: 20rpx 0;
    }
    .back-arrow {
        font-size: 40rpx;
        color: #2DD4BF;
    }
    .back-text {
        font-size: 28rpx;
        color: #2DD4BF;
    }
    .nav-title {
        font-size: 32rpx;
        font-weight: bold;
        color: #FFFFFF;
    }

    .summary-card {
        margin-bottom: 20rpx;
    }
    .summary-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20rpx 0;
        border-bottom: 1rpx solid #374151;
    }
    .summary-row:last-child {
        border-bottom: none;
    }
    .summary-label {
        font-size: 28rpx;
        color: #9CA3AF;
    }
    .summary-value {
        font-size: 30rpx;
        font-weight: bold;
        color: #FFFFFF;
        text-align: right;
        max-width: 60%;
    }

    .report-card {
        flex: 1;
        min-height: 500rpx;
    }
    .report-title {
        font-size: 30rpx;
        font-weight: bold;
        color: #2DD4BF;
        display: block;
        margin-bottom: 20rpx;
    }
    .report-scroll {
        max-height: 900rpx;
    }
    .report-text {
        font-size: 28rpx;
        color: #D1D5DB;
        line-height: 1.8;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .card {
        background-color: #1F2937;
        border-radius: 12px;
        padding: 30rpx;
        margin-bottom: 15rpx;
    }
</style>
