const ChartTheme = {
    colors: {
        primary: '#2b6cb0',
        secondary: '#718096',
        success: '#38a169',
        warning: '#dd6b20',
        danger: '#e53e3e',
        info: '#3182ce',
        purple: '#805ad5',
        pink: '#d53f8c',
        cyan: '#0bc5ea',
        
        background: {
            light: '#ffffff',
            dark: '#1a202c'
        },
        
        text: {
            primary: '#2d3748',
            secondary: '#718096'
        },
        
        grid: {
            light: '#e2e8f0',
            dark: '#4a5568'
        }
    },
    
    fonts: {
        family: "'Helvetica Neue', 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif",
        size: {
            small: 10,
            medium: 12,
            large: 14,
            xlarge: 16
        }
    },
    
    getChartOptions(type = 'line') {
        const isDark = document.body.classList.contains('dark-mode');
        
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        font: {
                            family: this.fonts.family,
                            size: this.fonts.size.medium
                        },
                        color: isDark ? this.colors.background.light : this.colors.text.primary,
                        padding: 15,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: isDark ? 'rgba(26, 32, 44, 0.9)' : 'rgba(255, 255, 255, 0.95)',
                    titleColor: isDark ? this.colors.background.light : this.colors.text.primary,
                    bodyColor: isDark ? this.colors.background.light : this.colors.text.secondary,
                    borderColor: this.colors.grid.light,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 6,
                    displayColors: true
                }
            },
            scales: {
                x: {
                    grid: {
                        color: isDark ? this.colors.grid.dark : this.colors.grid.light,
                        drawBorder: false
                    },
                    ticks: {
                        color: isDark ? this.colors.background.light : this.colors.text.secondary,
                        font: {
                            family: this.fonts.family,
                            size: this.fonts.size.small
                        }
                    }
                },
                y: {
                    grid: {
                        color: isDark ? this.colors.grid.dark : this.colors.grid.light,
                        drawBorder: false
                    },
                    ticks: {
                        color: isDark ? this.colors.background.light : this.colors.text.secondary,
                        font: {
                            family: this.fonts.family,
                            size: this.fonts.size.small
                        }
                    }
                }
            }
        };
        
        const typeOptions = {
            line: {
                elements: {
                    line: {
                        tension: 0.4,
                        borderWidth: 2
                    },
                    point: {
                        radius: 4,
                        hoverRadius: 6,
                        borderWidth: 2
                    }
                },
                fill: true
            },
            bar: {
                elements: {
                    bar: {
                        borderRadius: 4,
                        borderWidth: 0
                    }
                }
            },
            doughnut: {
                cutout: '60%',
                elements: {
                    arc: {
                        borderWidth: 0,
                        borderRadius: 4
                    }
                }
            },
            pie: {
                elements: {
                    arc: {
                        borderWidth: 0,
                        borderRadius: 4
                    }
                }
            },
            radar: {
                elements: {
                    line: {
                        borderWidth: 2
                    },
                    point: {
                        radius: 4,
                        hoverRadius: 6
                    }
                }
            },
            polarArea: {
                elements: {
                    arc: {
                        borderWidth: 0
                    }
                }
            }
        };
        
        return { ...baseOptions, ...typeOptions[type] };
    },
    
    getColorPalette(count = 6) {
        const palettes = [
            [this.colors.primary, this.colors.success, this.colors.warning, this.colors.danger, this.colors.purple, this.colors.cyan],
            [this.colors.success, this.colors.primary, this.colors.info, this.colors.warning, this.colors.purple, this.colors.pink],
            [this.colors.primary, this.colors.secondary, this.colors.success, this.colors.warning, this.colors.danger, this.colors.info]
        ];
        return palettes[count % palettes.length].slice(0, count);
    },
    
    createGradient(ctx, color1, color2) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    },
    
    exportChartAsImage(chart, filename = 'chart') {
        const link = document.createElement('a');
        link.download = `${filename}_${new Date().toISOString().slice(0, 10)}.png`;
        link.href = chart.toBase64Image();
        link.click();
    }
};

function createLineChart(ctx, labels, datasets, options = {}) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js 未加载，无法创建图表');
        return null;
    }
    
    const defaultOptions = ChartTheme.getChartOptions('line');
    
    const processedDatasets = datasets.map((dataset, index) => ({
        ...dataset,
        borderColor: dataset.borderColor || ChartTheme.getColorPalette(datasets.length)[index],
        backgroundColor: dataset.backgroundColor || ChartTheme.createGradient(
            ctx, 
            ChartTheme.getColorPalette(datasets.length)[index] + '40',
            ChartTheme.getColorPalette(datasets.length)[index] + '05'
        )
    }));
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: processedDatasets
        },
        options: { ...defaultOptions, ...options }
    });
}

function createBarChart(ctx, labels, datasets, options = {}) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js 未加载，无法创建图表');
        return null;
    }
    
    const defaultOptions = ChartTheme.getChartOptions('bar');
    
    const processedDatasets = datasets.map((dataset, index) => ({
        ...dataset,
        backgroundColor: dataset.backgroundColor || ChartTheme.getColorPalette(datasets.length)[index]
    }));
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: processedDatasets
        },
        options: { ...defaultOptions, ...options }
    });
}

function createDoughnutChart(ctx, labels, data, options = {}) {
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js 未加载，无法创建图表');
        return null;
    }
    
    const defaultOptions = ChartTheme.getChartOptions('doughnut');
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ChartTheme.getColorPalette(labels.length)
            }]
        },
        options: { ...defaultOptions, ...options }
    });
}

function createPieChart(ctx, labels, data, options = {}) {
    const defaultOptions = ChartTheme.getChartOptions('pie');
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ChartTheme.getColorPalette(labels.length)
            }]
        },
        options: { ...defaultOptions, ...options }
    });
}

function createRadarChart(ctx, labels, datasets, options = {}) {
    const defaultOptions = ChartTheme.getChartOptions('radar');
    
    const processedDatasets = datasets.map((dataset, index) => ({
        ...dataset,
        borderColor: dataset.borderColor || ChartTheme.getColorPalette(datasets.length)[index],
        backgroundColor: dataset.backgroundColor || ChartTheme.getColorPalette(datasets.length)[index] + '40',
        pointBackgroundColor: dataset.pointBackgroundColor || ChartTheme.getColorPalette(datasets.length)[index]
    }));
    
    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: processedDatasets
        },
        options: { ...defaultOptions, ...options }
    });
}

function createPolarAreaChart(ctx, labels, data, options = {}) {
    const defaultOptions = ChartTheme.getChartOptions('polarArea');
    
    return new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ChartTheme.getColorPalette(labels.length).map(c => c + '80')
            }]
        },
        options: { ...defaultOptions, ...options }
    });
}

function createComparisonChart(ctx, labels, datasets1, datasets2, options = {}) {
    const defaultOptions = ChartTheme.getChartOptions('line');
    
    const processedDatasets = [
        ...datasets1.map((dataset, index) => ({
            ...dataset,
            borderColor: ChartTheme.colors.primary,
            backgroundColor: ChartTheme.createGradient(ctx, ChartTheme.colors.primary + '40', ChartTheme.colors.primary + '05'),
            label: (dataset.label || '数据集 1') + ' (期间1)'
        })),
        ...datasets2.map((dataset, index) => ({
            ...dataset,
            borderColor: ChartTheme.colors.secondary,
            backgroundColor: ChartTheme.createGradient(ctx, ChartTheme.colors.secondary + '40', ChartTheme.colors.secondary + '05'),
            borderDash: [5, 5],
            label: (dataset.label || '数据集 1') + ' (期间2)'
        }))
    ];
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: processedDatasets
        },
        options: { 
            ...defaultOptions, 
            ...options,
            plugins: {
                ...defaultOptions.plugins,
                title: {
                    display: true,
                    text: '数据对比',
                    font: {
                        size: 16,
                        family: ChartTheme.fonts.family
                    },
                    color: ChartTheme.colors.text.primary
                }
            }
        }
    });
}
