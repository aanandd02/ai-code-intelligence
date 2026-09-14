import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

function CodeBlock({
  language,
  value,
}: {
  language: string;
  value: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        margin: '12px 0',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--border-default)',
        background: '#0a0d12',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '6px 12px',
          background: 'var(--bg-elevated)',
          borderBottom: '1px solid var(--border-muted)',
          fontSize: 11,
          fontFamily: 'monospace',
          color: 'var(--text-secondary)',
        }}
      >
        <span>{language || 'code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: 'transparent',
            border: 'none',
            color: copied ? 'var(--accent-green)' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 11,
            padding: '2px 6px',
            borderRadius: 4,
          }}
          title="Copy code"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: '12px 14px',
          overflowX: 'auto',
          fontSize: 13,
          lineHeight: 1.5,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          color: '#e6edf3',
        }}
      >
        <code>{value}</code>
      </pre>
    </div>
  );
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-body" style={{ color: 'var(--text-primary)', fontSize: 14, lineHeight: 1.65 }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: '18px 0 8px', color: 'var(--text-primary)' }}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: 17, fontWeight: 700, margin: '16px 0 8px', color: 'var(--text-primary)' }}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: '14px 0 6px', color: 'var(--text-primary)' }}>
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 style={{ fontSize: 14, fontWeight: 600, margin: '12px 0 4px', color: 'var(--text-primary)' }}>
              {children}
            </h4>
          ),
          p: ({ children }) => <p style={{ margin: '8px 0' }}>{children}</p>,
          strong: ({ children }) => (
            <strong style={{ fontWeight: 650, color: 'var(--text-primary)' }}>{children}</strong>
          ),
          em: ({ children }) => <em style={{ fontStyle: 'italic', color: 'var(--text-primary)' }}>{children}</em>,
          ul: ({ children }) => (
            <ul style={{ margin: '6px 0 6px 20px', listStyleType: 'disc', paddingLeft: 4 }}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: '6px 0 6px 20px', listStyleType: 'decimal', paddingLeft: 4 }}>
              {children}
            </ol>
          ),
          li: ({ children }) => <li style={{ margin: '4px 0' }}>{children}</li>,
          blockquote: ({ children }) => (
            <blockquote
              style={{
                margin: '10px 0',
                padding: '6px 14px',
                borderLeft: '3px solid var(--accent-blue)',
                background: 'rgba(88, 166, 255, 0.05)',
                color: 'var(--text-secondary)',
                borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
              }}
            >
              {children}
            </blockquote>
          ),
          hr: () => (
            <hr style={{ border: 'none', borderTop: '1px solid var(--border-default)', margin: '16px 0' }} />
          ),
          table: ({ children }) => (
            <div style={{ overflowX: 'auto', margin: '12px 0' }}>
              <table
                style={{
                  borderCollapse: 'collapse',
                  width: '100%',
                  fontSize: 13,
                  border: '1px solid var(--border-default)',
                }}
              >
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th
              style={{
                padding: '6px 12px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                fontWeight: 600,
                textAlign: 'left',
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              style={{
                padding: '6px 12px',
                border: '1px solid var(--border-default)',
              }}
            >
              {children}
            </td>
          ),
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !match && !String(children).includes('\n');
            const codeString = String(children).replace(/\n$/, '');

            if (!isInline) {
              return <CodeBlock language={match ? match[1] : ''} value={codeString} />;
            }

            return (
              <code
                style={{
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                  fontSize: '85%',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-muted)',
                  borderRadius: 4,
                  padding: '2px 6px',
                  color: 'var(--accent-blue)',
                }}
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
