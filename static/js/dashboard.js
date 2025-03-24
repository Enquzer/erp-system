document.addEventListener('DOMContentLoaded', function () {
    // Production Chart
    const productionCtx = document.getElementById('productionChart').getContext('2d');
    if (chartData.productionValues.length === 0 || chartData.productionValues.every(val => val === 0)) {
        document.getElementById('productionNoData').style.display = 'block';
        productionCtx.canvas.style.display = 'none';
    } else {
        new Chart(productionCtx, {
            type: 'bar',
            data: {
                labels: chartData.productionLabels,
                datasets: [{
                    label: 'Produced Quantity',
                    data: chartData.productionValues,
                    backgroundColor: '#F28C38'
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // Delivery Chart
    const deliveryCtx = document.getElementById('deliveryChart').getContext('2d');
    if (chartData.deliveryValues.length === 0 || chartData.deliveryValues.every(val => val === 0)) {
        document.getElementById('deliveryNoData').style.display = 'block';
        deliveryCtx.canvas.style.display = 'none';
    } else {
        new Chart(deliveryCtx, {
            type: 'bar',
            data: {
                labels: chartData.deliveryLabels,
                datasets: [{
                    label: 'Order Quantity',
                    data: chartData.deliveryValues,
                    backgroundColor: '#5B6D5B'
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // Delivery Status Chart
    const deliveryStatusCtx = document.getElementById('deliveryStatusChart').getContext('2d');
    if (chartData.deliveryStatusValues.every(val => val === 0)) {
        document.getElementById('deliveryStatusNoData').style.display = 'block';
        deliveryStatusCtx.canvas.style.display = 'none';
    } else {
        new Chart(deliveryStatusCtx, {
            type: 'pie',
            data: {
                labels: chartData.deliveryStatusLabels,
                datasets: [{
                    data: chartData.deliveryStatusValues,
                    backgroundColor: ['#1A3C34', '#F28C38']
                }]
            },
            options: {
                responsive: true
            }
        });
    }
});