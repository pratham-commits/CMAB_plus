# Part 0. Foundations from zero

[Back to the index](../GROUND_UP_GUIDE.md) · Next: [Part 1, the paper and Review I](01-paper-and-review1.md)

This part assumes no technical background. Each idea starts with an everyday picture and then gets its proper name. Later parts use only the names, so read this part once in order.

---

## 0.1 The internet moves small parcels called packets

Picture a long letter that you want to send to a friend in another city. Instead of posting it as one thick envelope, you cut it into hundreds of postcards, number each card, and post them separately. The postal system carries each card on whatever route is free. Your friend collects the cards, puts them back in order, and asks you to resend any card that never arrived.

The internet works the same way. Every file, web page and video is cut into small pieces called packets, usually about 1,500 bytes each. Each packet carries the address of the sender and the receiver. Routers along the way read the address and forward the packet one step closer. The receiving computer puts the packets back in order.

Three numbers describe how well this delivery works.

| Everyday picture | Technical name | Unit | What it means |
| --- | --- | --- | --- |
| How many postcards per second the post office can carry | Bandwidth (capacity) | bits per second, written Mbit/s or kbps | The most data the path can carry per second |
| How many postcards per second arrive for you | Throughput | Mbit/s or kbps | The rate you get, which is at most the bandwidth |
| How long one postcard takes to go there and a reply to come back | Round-trip time (RTT), often called latency | milliseconds (ms) | The delay of the path |
| How many postcards get lost | Packet loss | percent | The share of packets that never arrive and must be resent |

A few unit facts are used everywhere in this guide:

- 1 byte is 8 bits. Network speeds use bits.
- 1 kbps is 1,000 bits per second. 1 Mbit/s is 1,000 kbps.
- A video encoded at 6000 kbps needs 6 Mbit of data for every second of picture.

Bandwidth and latency are separate things. A water pipe is a good picture. The width of the pipe is the bandwidth; the length of the pipe is the latency. A wide pipe can be long (a satellite link with lots of capacity and a long delay) and a narrow pipe can be short (a slow but nearby connection).

## 0.2 Satellites, Starlink and handovers every 15 seconds

### Two kinds of satellite internet

Old satellite internet used satellites in geostationary orbit (GEO), about 35,786 km above the equator. At that height a satellite circles once per day, so it seems to hang still in the sky and a dish can point at it forever. The cost is distance: a signal needs roughly half a second for the round trip, which makes video calls and games painful.

Starlink, run by SpaceX, uses thousands of satellites in low Earth orbit (LEO), at about 550 km. The trip up and down is short, so the delay is close to that of ground internet. The MMSys '24 paper measured a median RTT to the Starlink gateway of 42.8 ms at a terminal without inter-satellite links and 109.0 ms at a terminal that uses them (Table 1 of the paper).

### Why the dish keeps switching satellites

A low satellite moves fast, about 7.5 km per second, and crosses the sky in a few minutes. So a dish on the ground cannot stay with one satellite. It has to switch to another one regularly. This switch is called a handover.

Starlink does something more specific. Researchers (Tanveer et al., CoNEXT '23) found that a global Starlink controller reassigns satellites to user terminals on a fixed 15-second schedule, at seconds 12, 27, 42 and 57 of every minute, at the same moments everywhere in the world. Zhao and Pan saw the same pattern: the RTT jumps at those four seconds of each minute. Starlink has not published why it uses this period; the 15-second timing is a measured fact, and the reasons behind it are not part of our project.

Analogy: think of a relay race where the runner changes every 15 seconds. Each baton pass costs a moment, and sometimes the baton is dropped. In network terms, at each handover the RTT goes up and some packets are lost.

The paper's emulator, which we reused, models a handover as one second in which delay rises from 40 ms to 100 ms and loss rises from 0.1% to 1%.

### What an inter-satellite link (ISL) is

Normally a Starlink satellite sends your traffic straight down to a ground station (a gateway) near you. In places with no ground station nearby, the satellites pass the traffic to each other with lasers until a satellite above a ground station can bring it down. These laser links between satellites are called inter-satellite links (ISLs).

The paper had a terminal in the Seychelles, an island nation in the Indian Ocean. No ground station is within 5,000 km, so its traffic crossed several ISLs before landing and reaching the Starlink point of presence in Lagos, Nigeria. Its RTT was higher and more variable: median 109.0 ms and standard deviation 43.7 ms, against 42.8 ms and 20.9 ms without ISLs. The artifact ships a one-hour RTT trace recorded at that Seychelles terminal, and our "trace shaper" replays it (Section 0.8).

## 0.3 How online video works

### Segments

A video player on the internet does not download one huge file. The server cuts the video into short pieces called segments. In our setup every segment is 2 seconds long. The player downloads segment 1, then segment 2, and so on, and plays them back to back.

### The bitrate ladder

Each segment is stored at several quality levels. A higher quality has a higher bitrate, which means more bits per second of video, a sharper picture and a bigger file. The list of available qualities is called the bitrate ladder, and each level is a rung.

Our ladder has eight rungs, in kbps:

```
rung index:   0     1     2     3     4     5     6     7
bitrate:     300   450   900  1200  1500  4900  5100  6000   (kbps)
```

Notice the big gap between rung 4 (1500 kbps) and rung 5 (4900 kbps). That gap matters a lot in Part 4.

Segment size is bitrate times duration. A 2-second segment at 6000 kbps holds 12,000 kbit, which is 12 Mbit. At 1500 kbps it holds 3 Mbit.

### The buffer

The player keeps a small stock of downloaded but not yet played video. This stock is the buffer, measured in seconds of video.

Analogy: a water tank on a roof. Water (video) flows in from the pipe (network) and flows out to the tap (the screen) at a steady rate of one second of video per second. If the inflow is slower than the outflow for a while, the tank empties.

### Rebuffering, also called a stall

When the buffer runs dry, the picture freezes and the player shows a spinning wheel while it waits for data. This freeze is called rebuffering or a stall. Viewers dislike stalls more than a slightly blurry picture, so avoiding stalls is a top goal.

A simple rule follows from the tank picture. If a segment takes longer to download than it takes to play, the buffer shrinks. For a 2-second segment:

```
download time = segment size / throughput
buffer change per segment ≈ 2 s of video gained − download time spent
```

Example: a 6000 kbps segment (12 Mbit) over a 4 Mbit/s link needs at least 3 seconds to download but only plays for 2 seconds. Each such segment costs the buffer at least 1 second. A 2-second buffer is gone after two segments.

## 0.4 Live video, live latency, the latency target and catch-up

### Video on demand versus live

For video on demand (VoD), such as a film, the whole video already exists. The player can download far ahead and keep tens of seconds in the buffer, so a short network problem goes unnoticed.

For live video, such as a cricket match, the next segment does not exist yet; the camera is still recording it. The player can only be as far ahead as the newest segment the server has published. The newest available point of the stream is called the live edge.

### Live latency

Live latency is how far behind the live edge the viewer is watching. If the bowler releases the ball at 8:00:00 and you see it at 8:00:03, your live latency is 3 seconds.

There is a trade-off. A larger live latency allows a bigger buffer, which protects against stalls, but your neighbour hears the crowd cheer before you see the wicket. Low-latency live streaming tries to keep latency at a few seconds.

### The latency target

The streaming service picks a latency target, for example 3 seconds. The player tries to hold its live latency near that value. Our experiments use targets of 3, 4, 5 and 6 seconds, the same as the paper. A 3-second target with 2-second segments leaves room for only one or two segments in the buffer, which makes it the hardest case.

### Catch-up by changing playback speed

When the player falls behind the target, for example after a stall, it cannot skip ahead without the viewer noticing a jump. Instead it plays slightly faster than normal for a while, so it slowly catches up. When it is too close to the live edge or the buffer is low, it can play slightly slower. This is called catch-up, and the controller that does it is the catch-up controller.

In our setup the playback rate can change by up to 0.17 in either direction, so speed stays between 0.83× and 1.17×. People rarely notice this range.

Playing faster also empties the buffer faster. If the network is already too slow, catching up makes stalls more likely. Keep that in mind for Part 3.

## 0.5 DASH, dash.js and ABR algorithms

### DASH

Dynamic Adaptive Streaming over HTTP (DASH) is a standard way to stream video over ordinary web servers. The server publishes a manifest file (called the MPD) that lists the segments and the rungs. The player fetches segments with normal web requests and picks a rung for each one.

### dash.js

dash.js is the open-source reference DASH player written in JavaScript; it runs inside a web browser. The paper's authors modified dash.js version 4.7.1 to add their algorithm. We used their modified copy.

### ABR algorithms

Before each segment, the player must decide which rung to download. The logic that makes this choice is the adaptive bitrate (ABR) algorithm.

Analogy: a delivery company decides, for each trip, whether to send a small van or a big truck. A big truck carries more (higher quality) but is slow on a narrow road and may arrive late (a stall). The ABR algorithm is the dispatcher.

A good ABR balances three things: high bitrate, few stalls, and live latency near the target.

### The three baselines in dash.js

dash.js ships three low-latency ABR algorithms. The paper compared its new algorithm against all three.

| Name | Plain-language idea | Technical description |
| --- | --- | --- |
| Dynamic | "Look at the recent download speed and at how full the tank is, and switch between the two views." | The dash.js default. Switches between a throughput rule and BOLA, a buffer-based rule. |
| L2A-LL (Learn2Adapt-LowLatency) | "Learn from each decision how wrong the last one was, and adjust step by step, without needing a speed forecast." | Online convex optimization; does not need a throughput model. |
| LoL+ | "Score each option on several QoE factors, learn the weights, and manage playback speed too." | Uses a self-organizing map to pick the rung, a QoE module, and its own playback-speed control. |

QoE means quality of experience, a combined score of how good the viewing felt (bitrate, stalls, latency, switches).

### dash.js rules and priorities

Inside dash.js, an ABR is built from rules. Each rule proposes a rung and attaches a priority: WEAK, DEFAULT or STRONG. dash.js takes the proposals at the highest priority present and, among those, the lowest rung. So a STRONG proposal wins over every DEFAULT proposal, including the throughput rule that would normally lower the rung on a slow link.

Analogy: several advisors suggest a truck size. Normal advice is pooled and the most careful suggestion wins. A STRONG suggestion is an order from the boss that the careful advisors cannot override.

This detail is the root of the bug we found.

### The throughput estimate

dash.js measures how fast each segment downloaded and keeps a smoothed average. It computes a fast-moving and a slow-moving average and takes the lower one, then multiplies by a safety factor of 0.9. The function is called `getSafeAverageThroughput`. The report writes the result as T̂ ("T-hat"); this guide calls it the safe throughput estimate. The half-lives of the averages (3 s and 8 s) come from our Review II code notes, not from the report.

## 0.6 TCP congestion control: CUBIC and BBR

### What TCP does

Video segments travel over TCP, the Transmission Control Protocol. TCP makes delivery reliable: it numbers packets, waits for acknowledgements, and resends lost packets.

TCP also decides how fast to send. If every sender pushed as fast as possible, routers would overflow and drop packets for everyone. So each sender runs a congestion control algorithm that guesses a fair, safe sending rate and keeps adjusting it. The amount of unacknowledged data a sender allows itself in flight is the congestion window (cwnd).

### CUBIC

CUBIC is the default congestion control in Linux. It is loss-based: it keeps increasing its window until a packet is lost, treats the loss as a sign that the road is full, and cuts the window. Then it grows again along a cubic curve, fast at first, slower near the old peak, fast again past it.

Analogy: a driver who speeds up until they hear a horn, then brakes hard, then speeds up again.

On a satellite path, packets can be lost for reasons other than a full queue, such as a handover. CUBIC still brakes on those losses.

### BBR

BBR (Bottleneck Bandwidth and Round-trip propagation time), designed at Google, is model-based. It keeps estimates of two numbers: the bottleneck bandwidth (the narrowest point of the path) and the minimum RTT. It then paces packets out at about the estimated bandwidth and periodically probes a little higher to see if more capacity is available. It does not cut its rate on every loss.

Analogy: a driver who measures the speed of the slowest lane and the shortest travel time, then drives at that speed and occasionally tries a little faster.

The MMSys '24 paper notes that TCP over Starlink suffers from repeated slow starts at handovers and names BBR as a candidate to do better than CUBIC. That sentence is why Review II tested BBR.

On Linux you choose the algorithm per machine with `sysctl net.ipv4.tcp_congestion_control=bbr` (or `cubic`). In our testbed the video is sent by the nginx web server, so we set it inside the nginx container.

## 0.7 Bandits: the learning idea inside CMAB

### The slot-machine picture

A casino has a row of slot machines, nicknamed one-armed bandits. Each machine pays out at a different hidden average. You have a limited number of coins. Every coin you spend on a machine you already know is good is called exploitation. Every coin you spend trying a machine you know little about is called exploration. Too much exploring wastes coins on bad machines; too little may miss the best one. Finding the balance is the multi-armed bandit problem. Each machine is an arm, each coin is a round, and the payout is the reward.

### Contextual bandit

Now suppose a screen above the machines shows some clues before each play, for example the time of day, and the best machine depends on the clues. A player who uses the clues is solving a contextual bandit problem. The clues are the context, written as a vector of numbers.

### Linear Thompson Sampling (LinTS)

Thompson sampling is one way to balance exploring and exploiting. For each arm, the player keeps a belief about its payout as a probability distribution: a best guess plus a spread that reflects uncertainty. Before each play:

1. For each arm, draw one random plausible payout from its belief.
2. Play the arm whose draw is highest.
3. Observe the reward and update the belief of the arm you played.

An arm you know little about has a wide spread, so it sometimes produces a high draw and gets tried. That is exploration without a separate rule for it. An arm you know is good has a narrow, high belief and gets picked often.

Linear Thompson sampling assumes that an arm's expected reward is a weighted sum of the context numbers, with weights that differ per arm. The belief is over those weights. An exploration parameter (alpha) scales the spread; the paper sets it to 1.0.

### CMAB in the MMSys '24 paper

The paper's algorithm, called CMAB here and "old CMAB" from Part 3 on, maps this as follows.

| Bandit idea | In the video player |
| --- | --- |
| Arm | A rung of the bitrate ladder (8 arms) |
| Round | One decision before downloading one segment |
| Context | Three measured numbers: network latency to the stats server, current playback speed, and estimated throughput |
| Learner | LinTS from the MABWiser Python library, run inside the browser through Pyodide (Python compiled to WebAssembly) |
| Reward | A QoE score for the chosen segment (below) |
| Memory | Only the decisions in the current 15-second slot; history is wiped at each handover |

The context does not include the buffer level, the live latency or the time since the handover. The handover awareness comes from two other places: the slot reset and a catch-up policy that slows playback around handover seconds.

The reward for a segment is:

```
reward = O.46 score × (target latency / current latency) × (chosen bitrate / top bitrate)
         − (share of the session's stall time that happened at the chosen bitrate)
```

O.46 is a 1-to-5 quality score from the ITU-T P.1203 video quality model. The three multiplied terms reward good picture quality, being on target, and a high bitrate. The subtracted term punishes a rung that has caused stalls.

Two facts about the code matter later. First, the artifact feeds P.1203 an empty list of stalls, so the O.46 score does not see stalls; stalls reach the reward only through the subtracted share, which is at most 1. Second, the code adds a forced window, described next.

### The forced exploration after each handover

Because memory is wiped at every slot boundary, the learner starts each slot with no data. The code handles this with a start-up rule. During the first |A| − 1 decisions of every slot, where |A| = 8 is the number of arms, so the first 7 decisions, the code skips LinTS and requests the top rung (6000 kbps). It sends that choice at STRONG priority, which overrides dash.js's throughput rule. Only from decision 8 of the slot does LinTS choose.

The paper's equations describe LinTS but do not describe this window or the STRONG priority. They are implementation details, and they are the core of what we found and fixed. A 15-second slot with 2-second segments holds only about 7 or 8 decisions, so the forced window covers almost the whole slot.

## 0.8 Emulation, simulation, real world, and the three shapers

### Three ways to test a network system

| Method | What runs | What is fake | Example |
| --- | --- | --- | --- |
| Simulation | A program that models packets and players with equations | Everything: the network, the player, the timing | A Python model of a buffer |
| Emulation | The real browser, real player code, real TCP in the Linux kernel | Only the network conditions, which are imposed on purpose | Our Docker testbed |
| Real world | Everything is real, including the satellite | Nothing | A Starlink dish on a roof |

Our project is emulation. The player, TCP stack and server are real software. The delay, loss and capacity are added by Linux on purpose. We had no Starlink dish.

### The traffic shaper: tc and netem

Linux has a tool called `tc` (traffic control) that can shape outgoing packets. Two parts of it matter here:

- netem (network emulator) adds delay and drops a chosen share of packets.
- A rate limiter caps the speed. The clock shaper uses a token bucket filter (TBF): picture a bucket that fills with tokens at a fixed rate, and a packet can leave only when it takes a token. The trace shaper uses a hierarchical token bucket (HTB), which is the same idea arranged in classes.

A queueing discipline (qdisc) is the name for one of these packet-handling stages attached to a network interface. In our testbed, the shaper runs inside the nginx container and shapes nginx's outgoing traffic toward the player.

### The three shapers used in this project

| Shaper | Script | Normal state | Handover state | Purpose |
| --- | --- | --- | --- | --- |
| Clock shaper ("paper clock") | `tc.py` | 100 Mbit/s, 40 ms delay, 0.1% loss | 50 Mbit/s, 100 ms, 1% loss during seconds 12, 27, 42, 57 | The paper's emulator; Review I and the fair Review II run |
| Capacity shaper ("capacity clock") | `tc.py` with set rate | 8, 4 or 1 Mbit/s, 40 ms, 0.1% loss | Same rate, 100 ms, 1% loss in the handover seconds | Our Review III test of a link that cannot carry the top rung |
| Trace shaper | `tc-trace.py` | Replays the Seychelles ISL RTT trace (one sample about every 10 ms, median RTT about 130 ms), 1% loss, 50 Mbit/s ceiling | Trace rows with RTT 0 or −1 become 100 ms, 100% loss, 20 Mbit/s ceiling | The harsher shaper shipped in the artifact |

The trace median RTT of about 130 ms comes from the final report. Our Review II notes say about 180 ms; use the report value.

The clock shaper is named after the wall clock: it switches state at fixed seconds of the minute. The trace shaper follows a recorded file instead. These are two different experiments, which is the lesson of Part 2.

## 0.9 How we measure results

The player logs samples of live latency, buffer level and bitrate throughout each 300-second session. For each session we compute three numbers.

| Metric | How it is computed | Good value |
| --- | --- | --- |
| Live latency (s) | Mean of the logged live latency samples | Close to the target |
| Rebuffer ratio (%) | Share of buffer samples at or below 0.05 s | 0% |
| Bitrate (kbps) | Mean of the logged bitrates that are above zero | High, as long as there are no stalls |

Two rules apply before any averaging.

- The 20% trim: drop the first 20% of each session's samples in time order. Start-up is always messy (the buffer is empty and the player is choosing its first rungs), and keeping it would mix start-up effects into every number.
- The 0.05 s threshold: a buffer sample at or below 0.05 s counts as stalled. The rebuffer ratio is therefore a sampled buffer-floor ratio. It is not the same as total frozen seconds divided by session length, which is what the paper reports. Our numbers and the paper's rebuffering numbers are related but not identical.

The same metric code was used for Reviews I, II and III, so all of our tables can be compared with each other.

## 0.10 Statistics in plain terms

### Rounds and sessions

One session is one 300-second playback with one ABR, one target and one network condition. A round is one repetition of the whole set of sessions. Network emulation is noisy (timing, packet drops, browser scheduling), so one session can mislead. Repeating each cell several times and averaging gives a steadier number. Review I and II used 10 rounds per cell; Review III used 5.

A cell is one combination, for example "CMAB+, 4 Mbit/s, CUBIC, 3 s target".

### Mean

The mean is the ordinary average of the per-session values in a cell.

### The 95% confidence interval

The mean of 5 sessions is only an estimate. A 95% confidence interval (CI) is a range around the mean that shows how uncertain that estimate is. Narrow means the sessions agreed; wide means they disagreed.

We use the Student-t interval:

```
CI half-width = t × (standard deviation of the session values) / √n
t = 2.776 for n = 5 sessions (4 degrees of freedom)
t = 2.262 for n = 10 sessions (9 degrees of freedom)
```

The t value is larger than the familiar 1.96 because with few samples we are less sure of the spread itself.

Worked example from our data. Review I, CMAB, 5 s target, ten sessions. Nine sessions had latency between 5.21 and 5.38 s. One session had 13.38 s. The mean is 6.05 s. The standard deviation is about 2.58 s, so the half-width is 2.262 × 2.58 / √10 ≈ 1.84 s. The result file records 6.048 ± 1.844 s. One bad session widened the interval from a few hundredths of a second to almost two seconds. That is what the large error bar at 5 s in the Review II figure shows (Part 4, Figure A).

How to read two intervals:

- If the intervals of two players do not overlap, the difference is very likely real for this setup.
- If they overlap, the data do not settle the question; the difference might be noise. Overlap does not prove the players are equal.

### Percentage points versus percent

If rebuffering falls from 81.14% to 14.67%, it fell by 66.47 percentage points, and by 81.9% in relative terms (66.47 / 81.14). The report's "71–86% reduction" on the trace is relative. "4–14 percentage points more rebuffering than L2A-LL" is absolute. Keep the two apart when answering questions.

---

[Back to the index](../GROUND_UP_GUIDE.md) · Next: [Part 1, the paper and Review I](01-paper-and-review1.md)
