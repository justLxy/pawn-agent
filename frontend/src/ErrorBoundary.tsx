import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

/**
 * 顶层错误边界：任何渲染期异常（如跨版本旧存档字段缺失导致的 .map 报错）
 * 不再让整站白屏，而是展示可重试/回大堂的降级界面。
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error?.message || '未知错误' }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // 便于线上排查：把异常与组件栈打到控制台（不上报第三方）
    console.error('页面渲染出错：', error, info?.componentStack)
  }

  private handleReload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <div
        role="alert"
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px',
          padding: '24px',
          textAlign: 'center',
          background: '#1a1512',
          color: '#e8dcc8',
          fontFamily: 'inherit',
        }}
      >
        <div style={{ fontSize: '48px' }}>🏮</div>
        <h1 style={{ fontSize: '20px', margin: 0 }}>柜台出了点岔子</h1>
        <p style={{ maxWidth: '420px', lineHeight: 1.6, opacity: 0.8, margin: 0 }}>
          页面遇到一个意外错误，你的进度已经保存在服务器上，不会丢失。刷新一下通常就能继续经营。
        </p>
        <button
          onClick={this.handleReload}
          style={{
            marginTop: '8px',
            padding: '10px 28px',
            fontSize: '15px',
            borderRadius: '8px',
            border: '1px solid #c9a26a',
            background: '#c9a26a',
            color: '#1a1512',
            cursor: 'pointer',
          }}
        >
          刷新重试
        </button>
        {this.state.message && (
          <details style={{ marginTop: '12px', maxWidth: '420px', opacity: 0.6 }}>
            <summary style={{ cursor: 'pointer', fontSize: '13px' }}>错误详情</summary>
            <pre style={{ whiteSpace: 'pre-wrap', textAlign: 'left', fontSize: '12px' }}>
              {this.state.message}
            </pre>
          </details>
        )}
      </div>
    )
  }
}

export default ErrorBoundary
