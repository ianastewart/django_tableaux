// Breakpoint handler class
class BreakpointHandler {
//TODO pass from django context
    static DEFAULT_BREAKPOINTS = {
        sm: 576,
        md: 768,
        lg: 992,
        xl: 1200,
        xxl: 1400
    };

    constructor(breakpoints) {

        this.breakpoints = breakpoints || BreakpointHandler.DEFAULT_BREAKPOINTS;
        this.currentBreakpoint = this.getCurrentBreakpoint();
        this.callbacks = {
            enter: {},  // Callbacks for entering a breakpoint
            leave: {}   // Callbacks for leaving a breakpoint
        };

        Object.keys(this.breakpoints).forEach(breakpoint => {
            this.onEnter(breakpoint, () => {
                const currentUrl = window.location.pathname + window.location.search;
                const url = new URL(currentUrl, window.location.origin);
                    url.searchParams.set('_bp', breakpoint);
                    window.location.href = url.toString();
                    // htmx.ajax('GET', url.toString(), {
                    //     target: 'body',
                    //     swap: 'innerHTML',
                    // });
                    // }
                })
        })


        // Add resize listener
        window.addEventListener('resize', () => this.handleResize());
    }

    getCurrentBreakpoint() {
        const width = window.innerWidth;
        let current = null;

        // Find the largest breakpoint that the current width is greater than or equal to
        Object.entries(this.breakpoints)
            .sort(([, a], [, b]) => a - b)
            .forEach(([name, size]) => {
                if (width >= size) {
                    current = name;
                }
            });

        return current;
    }

    getBreakpointUrl(url) {
        // Create URL object for easier manipulation
        const urlObj = new URL(url);
        const breakpoint = this.getCurrentBreakpoint();

        // Set the breakpoint parameter
        urlObj.searchParams.set('bp', breakpoint);
        return urlObj.toString();
    }

    handleResize() {
        const newBreakpoint = this.getCurrentBreakpoint();

        // If breakpoint changed
        if (newBreakpoint !== this.currentBreakpoint) {
            // Call leave callbacks for old breakpoint
            if (this.currentBreakpoint && this.callbacks.leave[this.currentBreakpoint]) {
                this.callbacks.leave[this.currentBreakpoint].forEach(callback => callback());
            }

            // Call enter callbacks for new breakpoint
            if (newBreakpoint && this.callbacks.enter[newBreakpoint]) {
                this.callbacks.enter[newBreakpoint].forEach(callback => callback());
            }

            this.currentBreakpoint = newBreakpoint;
        }
    }

    // Add callback for entering a breakpoint
    onEnter(breakpoint, callback) {
        if (!this.callbacks.enter[breakpoint]) {
            this.callbacks.enter[breakpoint] = [];
        }
        this.callbacks.enter[breakpoint].push(callback);

        // Execute callback immediately if we're already at this breakpoint
        if (this.currentBreakpoint === breakpoint) {
            callback();
        }
    }

    //
    // // Add callback for leaving a breakpoint
    // onLeave(breakpoint, callback) {
    //     if (!this.callbacks.leave[breakpoint]) {
    //         this.callbacks.leave[breakpoint] = [];
    //     }
    //     this.callbacks.leave[breakpoint].push(callback);
    // }
}

