module.exports = {
  title: 'Hajimi',
  description: 'Gemini API 反向代理服务 - 高性能、多功能的 AI 接口解决方案',
  base: '/hajimi/',
  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['meta', { name: 'theme-color', content: '#667eea' }],
    ['meta', { name: 'keywords', content: 'Gemini, API, 反向代理, AI, OpenAI, Docker, 部署' }]
  ],
  themeConfig: {
    nav: [
      { text: '🏠 首页', link: '/' },
      { text: '🚀 快速开始', link: '/deploy/' },
      { text: '📖 使用指南', link: '/usage/' },
      { 
        text: '🔗 相关链接', 
        items: [
          { text: 'GitHub 仓库', link: 'https://github.com/wyeeeee/hajimi' },
          { text: '问题反馈', link: 'https://github.com/wyeeeee/hajimi/issues' },
          { text: 'Gemini API', link: 'https://makersuite.google.com/app/apikey' }
        ]
      }
    ],
    sidebar: {
      '/deploy/': [
        {
          title: '部署指南',
          collapsable: false,
          children: [
            '',
            'docker',
            'huggingface', 
            'claw',
            'zeabur',
            'termux',
            'vertex'
          ]
        }
      ],
      '/usage/': [
        {
          title: '使用说明',
          collapsable: false,
          children: [
            '',
            'configuration',
            'troubleshooting'
          ]
        }
      ],
      '/': [
        {
          title: '文档导航',
          collapsable: false,
          children: [
            ['/', '📋 项目介绍'],
            ['/deploy/', '🚀 部署指南'],
            ['/usage/', '📖 使用说明']
          ]
        }
      ]
    },
    lastUpdated: '最后更新时间',
    smoothScroll: true,
    repo: 'wyeeeee/hajimi',
    repoLabel: 'GitHub',
    editLinks: true,
    editLinkText: '在 GitHub 上编辑此页',
    nextLinks: true,
    prevLinks: true
  },
  plugins: [
    '@vuepress/back-to-top',
    '@vuepress/medium-zoom'
  ],
  markdown: {
    lineNumbers: true,
    extractHeaders: ['h2', 'h3', 'h4']
  }
}