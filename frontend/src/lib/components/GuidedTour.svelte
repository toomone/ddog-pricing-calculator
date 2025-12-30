<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { driver, type Driver, type DriveStep } from 'driver.js';
	import 'driver.js/dist/driver.css';

	const TOUR_STORAGE_KEY = 'pricehound_tour_completed';

	let driverInstance: Driver | null = null;
	let tourCompleted = false;

	// Tour steps configuration
	const steps: DriveStep[] = [
		{
			element: '#region-selector',
			popover: {
				title: 'Select Your Region',
				description: 'Choose the Datadog region where your data is hosted. Pricing may vary by region.',
				side: 'bottom',
				align: 'start'
			}
		},
		{
			element: '#product-search',
			popover: {
				title: 'Search Products',
				description: 'Search and add Datadog products to estimate your costs. Adjust quantities as needed.',
				side: 'bottom',
				align: 'start'
			}
		},
		{
			element: '#action-buttons',
			popover: {
				title: 'Quick Actions',
				description: 'Use predefined templates for common use cases, or estimate your log indexing costs with the built-in calculator.',
				side: 'top',
				align: 'start'
			}
		},
		{
			element: '#share-button',
			popover: {
				title: 'Share & Export',
				description: 'Create a shareable public URL, export to CSV/JSON, or print your quote when ready.',
				side: 'bottom',
				align: 'end'
			}
		}
	];

	function startTour() {
		if (!browser) return;

		driverInstance = driver({
			showProgress: true,
			steps,
			nextBtnText: 'Next →',
			prevBtnText: '← Back',
			doneBtnText: 'Get Started!',
			progressText: '{{current}} of {{total}}',
			onDestroyed: () => {
				markTourCompleted();
			}
		});

		driverInstance.drive();
	}

	function markTourCompleted() {
		if (browser) {
			localStorage.setItem(TOUR_STORAGE_KEY, 'true');
			tourCompleted = true;
		}
	}

	function resetTour() {
		if (browser) {
			localStorage.removeItem(TOUR_STORAGE_KEY);
			tourCompleted = false;
			// Small delay to ensure DOM is ready
			setTimeout(() => startTour(), 100);
		}
	}

	onMount(() => {
		if (browser) {
			tourCompleted = localStorage.getItem(TOUR_STORAGE_KEY) === 'true';
			
			// Auto-start tour for first-time visitors after a short delay
			if (!tourCompleted) {
				setTimeout(() => startTour(), 500);
			}
		}
	});

	onDestroy(() => {
		if (driverInstance) {
			driverInstance.destroy();
		}
	});

	// Expose functions for external control
	export { startTour, resetTour, tourCompleted };
</script>

<!-- Restart Tour Button (shown after tour is completed) -->
{#if tourCompleted}
	<button
		type="button"
		on:click={resetTour}
		class="fixed bottom-20 right-4 z-50 inline-flex items-center gap-2 rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background shadow-lg transition-all hover:scale-105 hover:bg-foreground/90"
		title="Restart guided tour"
	>
		<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<circle cx="12" cy="12" r="10" />
			<path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
			<path d="M12 17h.01" />
		</svg>
		<span class="hidden sm:inline">Tour</span>
	</button>
{/if}

<style>
	/* Custom driver.js styling to match app theme */
	:global(.driver-popover) {
		background: hsl(var(--card)) !important;
		color: hsl(var(--card-foreground)) !important;
		border: 1px solid hsl(var(--border)) !important;
		border-radius: 0.75rem !important;
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
	}

	:global(.driver-popover-title) {
		font-size: 1.125rem !important;
		font-weight: 600 !important;
		color: hsl(var(--foreground)) !important;
	}

	:global(.driver-popover-description) {
		color: hsl(var(--muted-foreground)) !important;
		font-size: 0.875rem !important;
		line-height: 1.5 !important;
	}

	:global(.driver-popover-progress-text) {
		color: hsl(var(--muted-foreground)) !important;
		font-size: 0.75rem !important;
	}

	:global(.driver-popover-prev-btn),
	:global(.driver-popover-next-btn) {
		background: hsl(var(--muted)) !important;
		color: hsl(var(--foreground)) !important;
		border: 1px solid hsl(var(--border)) !important;
		border-radius: 0.375rem !important;
		font-weight: 500 !important;
		font-size: 0.875rem !important;
		padding: 0.5rem 1rem !important;
		transition: background-color 0.2s, border-color 0.2s !important;
		outline: none !important;
		box-shadow: none !important;
	}

	:global(.driver-popover-prev-btn:hover),
	:global(.driver-popover-next-btn:hover) {
		background: hsl(var(--accent)) !important;
	}

	:global(.driver-popover-prev-btn:focus),
	:global(.driver-popover-next-btn:focus) {
		outline: none !important;
		box-shadow: none !important;
	}

	:global(.driver-popover-next-btn) {
		background: hsl(var(--foreground)) !important;
		color: hsl(var(--background)) !important;
		border-color: hsl(var(--foreground)) !important;
	}

	:global(.driver-popover-next-btn:hover) {
		background: hsl(var(--foreground) / 0.9) !important;
	}

	:global(.driver-popover-next-btn:focus),
	:global(.driver-popover-next-btn:active) {
		background: hsl(var(--foreground)) !important;
		outline: none !important;
		box-shadow: none !important;
	}

	:global(.driver-popover button) {
		outline: none !important;
		box-shadow: none !important;
		text-shadow: none !important;
		-webkit-font-smoothing: antialiased !important;
		-moz-osx-font-smoothing: grayscale !important;
	}

	:global(.driver-popover button::before),
	:global(.driver-popover button::after) {
		content: none !important;
		display: none !important;
	}

	:global(.driver-popover-close-btn) {
		color: hsl(var(--muted-foreground)) !important;
	}

	:global(.driver-popover-close-btn:hover) {
		color: hsl(var(--foreground)) !important;
	}

	:global(.driver-popover-arrow-side-bottom) {
		border-bottom-color: hsl(var(--card)) !important;
	}

	:global(.driver-popover-arrow-side-top) {
		border-top-color: hsl(var(--card)) !important;
	}

	:global(.driver-popover-arrow-side-left) {
		border-left-color: hsl(var(--card)) !important;
	}

	:global(.driver-popover-arrow-side-right) {
		border-right-color: hsl(var(--card)) !important;
	}

	/* Highlight styling */
	:global(.driver-active-element) {
		outline: 2px solid hsl(262, 83%, 58%) !important;
		outline-offset: 2px !important;
		border-radius: 0.5rem !important;
	}

	:global(.driver-overlay) {
		background: rgba(0, 0, 0, 0.7) !important;
	}
</style>

